# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Explicit writer fences: conditional updates and shared parent locks.

Retirement and restore deliberately do not refresh row ``updated`` timestamps
because the locked recapture fingerprint uses them as concurrency authority.
SQLite acquires its RESERVED lock before each guard reads authority, rather than
waiting for the later flush, so retirement cannot pass between the two actions.
"""

from typing import Any, Dict, Sequence, Set, Union
from uuid import UUID

from sqlalchemy import func, inspect, or_, select, update
from sqlalchemy.orm.attributes import set_committed_value
from sqlmodel import Session, col
from sqlmodel.sql.expression import SelectOfScalar

from zenml.enums import ArchiveBundleStatus, RetentionFailure
from zenml.exceptions import (
    ExecutionArchivedError,
    ExecutionRetentionConflictError,
    IllegalOperationError,
)
from zenml.zen_stores.retention import transactions
from zenml.zen_stores.schemas import (
    ArchiveBundleSchema,
    PipelineRunSchema,
    PipelineSnapshotSchema,
    StepRunSchema,
)

HotRow = Union[PipelineRunSchema, StepRunSchema]


def update_hot(session: Session, row: HotRow) -> None:
    """Carry the archive predicate in the existing row update, without a SELECT.

    Callers must modify the row and invoke this function inside no_autoflush
    so an ORM flush cannot publish an unfenced update first.
    Step updates can lock a step before their run while retirement locks the
    run first; MySQL may reject either participant as a deadlock victim and the
    archive pass retries that transient failure.

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
        root_run_id = (
            row.pipeline_run.root_run_id or row.pipeline_run.id
            if isinstance(row, StepRunSchema)
            else row.root_run_id or row.id
        )
        raise ExecutionArchivedError.for_entity(row.id, root_run_id)
    # The conditional statement replaces this ORM flush, not an extra write.
    for column_name, column_value in changes.items():
        set_committed_value(row, column_name, column_value)


def protect_inserts(
    session: Session,
    run_ids: Union[Sequence[UUID], SelectOfScalar[UUID]],
    *,
    exclusive: bool = False,
) -> None:
    """Hold target run locks and check one indexed active-slot query per batch.

    Args:
        session: Current transaction, before inserting any referenced detail.
        run_ids: Authorized target IDs or a scalar child-owner query. A query
            must identify exactly one run; it executes inside the locking read.
        exclusive: Preserve an existing exclusive lock required by the writer.

    Raises:
        ExecutionArchivedError: If a target's detail is archived.
        ExecutionRetentionConflictError: If a target disappeared or has an active claim.
    """
    transactions.begin_write(session)
    if isinstance(run_ids, SelectOfScalar):
        ids: Union[Sequence[UUID], SelectOfScalar[UUID]] = run_ids
        expected_count = 1
    else:
        ids = sorted(set(run_ids))
        expected_count = len(ids)
        if not ids:
            return
    # Step creation expires its run before locking; hydrate that same identity
    # here so accessing its current snapshot does not issue another SELECT.
    rows = (
        session.execute(
            select(PipelineRunSchema)
            .execution_options(populate_existing=True)
            .where(col(PipelineRunSchema.id).in_(ids))
            .order_by(col(PipelineRunSchema.id))
            .with_for_update(read=not exclusive)
        )
        .scalars()
        .all()
    )
    if len(rows) != expected_count:
        raise ExecutionRetentionConflictError(
            "Execution disappeared before detail insertion.",
            error_code=RetentionFailure.BUSY,
        )
    roots = sorted({row.root_run_id or row.id for row in rows})
    for row in rows:
        if row.archive_bundle_id is not None:
            raise ExecutionArchivedError.for_entity(
                row.id, row.root_run_id or row.id
            )
    # The run locks already serialize retirement; locking the slot too would
    # invert the archive lock order and can deadlock unrelated writers.
    active = session.execute(
        select(col(ArchiveBundleSchema.active_root_id)).where(
            col(ArchiveBundleSchema.active_root_id).in_(roots),
            col(ArchiveBundleSchema.status).in_(
                ArchiveBundleStatus.writer_protected()
            ),
            or_(
                col(ArchiveBundleSchema.status) != ArchiveBundleStatus.PENDING,
                col(ArchiveBundleSchema.claim_expires_at).is_(None),
                col(ArchiveBundleSchema.claim_expires_at)
                > func.current_timestamp(),
            ),
        )
    ).first()
    if active is not None:
        raise ExecutionRetentionConflictError(
            f"Retention is in progress for execution root '{active[0]}'. Retry after the operation completes.",
            error_code=RetentionFailure.BUSY,
        )


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
    transactions.begin_write(session)
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
            "Snapshot disappeared before ownership mutation.",
            error_code=RetentionFailure.BUSY,
        )
    for row in rows:
        if row.archive_bundle_id is not None:
            raise ExecutionArchivedError.for_entity(row.id, None)


def protect_membership(session: Session, run_ids: Sequence[UUID]) -> Set[UUID]:
    """Lock canonical roots before adding a child, pin or model association.

    Args:
        session: Current mutation transaction.
        run_ids: Existing association targets, resolved and authorized by caller.

    Returns:
        Roots whose detail is already archived.

    Raises:
        ExecutionRetentionConflictError: If none of the referenced roots survives.
    """
    transactions.begin_write(session)
    if not run_ids:
        return set()
    roots = (
        select(
            func.coalesce(
                col(PipelineRunSchema.root_run_id), col(PipelineRunSchema.id)
            )
        )
        .where(col(PipelineRunSchema.id).in_(run_ids))
        .distinct()
    )
    rows = session.execute(
        select(
            col(PipelineRunSchema.id), col(PipelineRunSchema.archive_bundle_id)
        )
        .where(col(PipelineRunSchema.id).in_(roots))
        .order_by(col(PipelineRunSchema.id))
        .with_for_update()
    ).all()
    if not rows:
        raise ExecutionRetentionConflictError(
            "Execution root disappeared before membership mutation.",
            error_code=RetentionFailure.BUSY,
        )
    return {row.id for row in rows if row.archive_bundle_id is not None}
