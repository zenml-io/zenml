# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Writer fences that keep ordinary writes off archived rows.

Updates to runs and steps carry a still-hot condition in the UPDATE itself.
Writes that add detail to a run, or new uses to a snapshot, first lock the
owner row and check its marker. Retirement locks the same rows, so either the
write commits first and retirement's locked recapture sees it, or retirement
commits first and the writer sees the marker. On SQLite nothing is ever
archived, and ``FOR UPDATE`` compiles to nothing, so these fences cost only
the reads.
"""

from typing import Any, Dict, Sequence, Union
from uuid import UUID

from sqlalchemy import inspect, select, update
from sqlalchemy.orm.attributes import set_committed_value
from sqlmodel import Session, col

from zenml.exceptions import (
    ExecutionArchivedError,
    ExecutionRetentionConflictError,
    IllegalOperationError,
)
from zenml.zen_stores.schemas import (
    PipelineRunSchema,
    PipelineSnapshotSchema,
    StepRunSchema,
)

HotRow = Union[PipelineRunSchema, StepRunSchema]


def update_hot(session: Session, row: HotRow) -> None:
    """Carry the archive predicate in the existing row update, without a SELECT.

    Callers must modify the row and invoke this function inside no_autoflush
    so an ORM flush cannot publish an unfenced update first. Step updates can
    lock a step before its run while retirement locks the run first; MySQL
    then rolls one of them back, and the archive pass skips that run.

    Args:
        session: Current transaction, before the row can autoflush.
        row: Modified existing run or step row.

    Raises:
        IllegalOperationError: If the row is not a persistent SQL identity.
        ExecutionArchivedError: If retirement won the concurrent row lock.
    """
    state = inspect(row)
    if state is None or not state.persistent:
        raise IllegalOperationError(
            "Conditional retention writes require an existing row."
        )
    changes: Dict[str, Any] = {
        attribute.key: state.dict[attribute.key]
        for attribute in state.mapper.column_attrs
        if state.attrs[attribute.key].history.has_changes()
    }
    if not changes:
        return
    schema = type(row)
    statement = (
        update(schema)
        .where(
            col(schema.id) == row.id,
            col(schema.archive_bundle_id).is_(None),
        )
        .values(**changes)
    )
    if session.connection().execute(statement).rowcount != 1:
        run_id = (
            row.pipeline_run_id if isinstance(row, StepRunSchema) else row.id
        )
        raise ExecutionArchivedError.for_entity(row.id, run_id)
    # The conditional statement replaces this ORM flush, not an extra write.
    for column_name, column_value in changes.items():
        set_committed_value(row, column_name, column_value)


def protect_run(session: Session, run_id: UUID) -> None:
    """Lock the run new detail will belong to and require it in SQL.

    Step creation locks its run anyway; this read doubles as that lock and
    loads the run so the caller's later access costs no extra SELECT.

    Args:
        session: Current transaction, before inserting the detail.
        run_id: Run that will own the new detail.

    Raises:
        ExecutionArchivedError: If the run is archived.
        ExecutionRetentionConflictError: If the run disappeared.
    """
    run = session.execute(
        select(PipelineRunSchema)
        .execution_options(populate_existing=True)
        .where(col(PipelineRunSchema.id) == run_id)
        .with_for_update()
    ).scalar_one_or_none()
    if run is None:
        raise ExecutionRetentionConflictError(
            "Execution disappeared before detail insertion."
        )
    if run.archive_bundle_id is not None:
        raise ExecutionArchivedError.for_entity(run.id, run.id)


def protect_snapshot_owners(
    session: Session,
    snapshot_ids: Sequence[UUID],
) -> None:
    """Serialize ownership changes on the snapshot itself, not all sharing runs.

    Args:
        session: Current association mutation transaction.
        snapshot_ids: Resolved snapshots whose owner sets will change.

    Raises:
        ExecutionRetentionConflictError: If an owner snapshot disappeared.
        ExecutionArchivedError: If new operational use targets archived detail.
    """
    if not snapshot_ids:
        return
    ids = sorted(set(snapshot_ids))
    rows = session.execute(
        select(
            col(PipelineSnapshotSchema.id),
            col(PipelineSnapshotSchema.archive_bundle_id),
        )
        .where(col(PipelineSnapshotSchema.id).in_(ids))
        .order_by(col(PipelineSnapshotSchema.id))
        .with_for_update()
    ).all()
    if len(rows) != len(ids):
        raise ExecutionRetentionConflictError(
            "Snapshot disappeared before ownership mutation."
        )
    for row in rows:
        if row.archive_bundle_id is not None:
            raise ExecutionArchivedError.for_entity(row.id, None)
