# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Writer fences that keep ordinary writes off archived rows.

Writes that add detail to a run, or new uses to a snapshot, first lock the
owner row and check its marker. Retirement locks the same rows, so either the
write commits first and retirement's locked recapture sees it, or retirement
commits first and the writer sees the marker. On SQLite nothing is ever
archived, and ``FOR UPDATE`` compiles to nothing, so these fences cost only
the reads.
"""

from uuid import UUID

from sqlalchemy import select
from sqlmodel import Session, col

from zenml.exceptions import (
    ExecutionArchivedError,
    ExecutionRetentionConflictError,
)
from zenml.zen_stores.schemas import (
    PipelineRunSchema,
    PipelineSnapshotSchema,
)


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


def lock_unarchived_snapshot(session: Session, snapshot_id: UUID) -> None:
    """Lock a snapshot and require its detail before creating a new use.

    Args:
        session: Transaction that will commit the new use.
        snapshot_id: Snapshot whose detail must remain available.

    Raises:
        ExecutionRetentionConflictError: If the snapshot disappeared.
        ExecutionArchivedError: If the snapshot's detail is archived.
    """
    row = session.execute(
        select(
            col(PipelineSnapshotSchema.id),
            col(PipelineSnapshotSchema.archive_bundle_id),
        )
        .where(col(PipelineSnapshotSchema.id) == snapshot_id)
        .with_for_update()
    ).one_or_none()
    if row is None:
        raise ExecutionRetentionConflictError(
            "Snapshot disappeared before ownership mutation."
        )
    if row.archive_bundle_id is not None:
        raise ExecutionArchivedError.for_entity(row.id, None)
