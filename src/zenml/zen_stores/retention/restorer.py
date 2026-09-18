# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Synchronous, all-or-nothing restore of one archived run.

The bundle is downloaded and verified outside SQL. One transaction then
locks the run, its steps, and its snapshots in the retirement lock order,
requires every archived identity to still exist with this bundle's marker,
writes the detail back, recreates the step configurations, and records the
restore time on the bundle row. Any mismatch rolls the whole restore back.
A concurrent second restore finds the marker already cleared and reports a
no-op.
"""

from typing import Any, Dict, Sequence
from uuid import UUID

from sqlalchemy import Engine, bindparam, insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, SQLModel, col

from zenml.enums import RestoreOutcome
from zenml.exceptions import (
    ExecutionRetentionConflictError,
    ExecutionRetentionIntegrityError,
)
from zenml.models.v2.misc.retention import RestoreResponse
from zenml.zen_stores.retention import transactions
from zenml.zen_stores.retention.format import (
    ArchiveDocument,
    Record,
    SnapshotRecord,
    StepRecord,
    decode,
)
from zenml.zen_stores.retention.storage import ArchiveStorage
from zenml.zen_stores.schemas import (
    ArchiveBundleSchema,
    PipelineRunSchema,
    StepConfigurationSchema,
)


def restore_run(
    engine: Engine, storage: ArchiveStorage, run_id: UUID
) -> RestoreResponse:
    """Write an archived run's detail back into SQL.

    Args:
        engine: Metadata database.
        storage: Archive storage.
        run_id: Authorized run.

    Returns:
        Restored, or a no-op when the run's detail is already in SQL.

    Raises:
        ExecutionRetentionIntegrityError: The marker has no bundle row, or
            the object holds another run's detail.
        ExecutionRetentionConflictError: A restored configuration identity
            or owner is already in use.
    """
    with Session(engine) as session:
        root = session.execute(
            select(
                col(PipelineRunSchema.id),
                col(PipelineRunSchema.archive_bundle_id),
            ).where(col(PipelineRunSchema.id) == run_id)
        ).one_or_none()
        if root is None:
            raise ExecutionRetentionConflictError(
                "The run disappeared before restoration started."
            )
        if root.archive_bundle_id is None:
            return RestoreResponse(run_id=run_id, outcome=RestoreOutcome.NOOP)
        bundle = session.get(ArchiveBundleSchema, root.archive_bundle_id)
        if bundle is None:
            raise ExecutionRetentionIntegrityError(
                "Archive marker has no bundle record."
            )
        bundle_id, project_id = bundle.id, bundle.project_id
        uri, size_bytes, content_hash = (
            bundle.uri,
            bundle.size_bytes,
            bundle.content_hash,
        )
    data = storage.read(uri, size_bytes)
    if len(data) != size_bytes:
        raise ExecutionRetentionIntegrityError(
            "Archive object size differs from its bundle record."
        )
    document = decode(data, content_hash)
    if document.run_id != run_id or document.project_id != project_id:
        raise ExecutionRetentionIntegrityError(
            "Archive content belongs to another run."
        )
    try:
        with transactions.transaction(engine) as session:
            return _apply(session, document, bundle_id)
    except IntegrityError as error:
        raise ExecutionRetentionConflictError(
            "A restored configuration identity or owner is already in use."
        ) from error


def _apply(
    session: Session, document: ArchiveDocument, bundle_id: UUID
) -> RestoreResponse:
    """Check identities under locks, then write every record back.

    Args:
        session: Restore transaction.
        document: Verified archive document.
        bundle_id: Bundle the run's marker must still name.

    Returns:
        The restored outcome, or a no-op when another restore won.

    Raises:
        ExecutionRetentionConflictError: The marker names another bundle.
    """
    root = session.execute(
        select(
            col(PipelineRunSchema.id),
            col(PipelineRunSchema.project_id),
            col(PipelineRunSchema.snapshot_id),
            col(PipelineRunSchema.archive_bundle_id),
        )
        .where(col(PipelineRunSchema.id) == document.run_id)
        .with_for_update()
    ).one_or_none()
    if root is None:
        raise ExecutionRetentionConflictError(
            "The run disappeared while its archive was being read."
        )
    if root.archive_bundle_id is None:
        return RestoreResponse(
            run_id=document.run_id, outcome=RestoreOutcome.NOOP
        )
    if root.archive_bundle_id != bundle_id:
        raise ExecutionRetentionConflictError(
            "The run was archived again while restoring."
        )
    if (
        root.project_id != document.project_id
        or root.project_id != document.run.project_id
        or root.snapshot_id != document.run.snapshot_id
    ):
        raise ExecutionRetentionConflictError(
            "The archived run changed its owner or snapshot."
        )
    _require_rows(session, "step_run", document.steps, bundle_id)
    _require_rows(session, "pipeline_snapshot", document.snapshots, bundle_id)
    _require_free_configurations(session, document)
    _write_back(session, document, bundle_id)
    restored_at = transactions.database_now(session)
    session.execute(
        update(ArchiveBundleSchema)
        .where(col(ArchiveBundleSchema.id) == bundle_id)
        .values(restored_at=restored_at)
    )
    return RestoreResponse(
        run_id=document.run_id,
        outcome=RestoreOutcome.RESTORED,
        restored_at=restored_at,
    )


def _require_rows(
    session: Session,
    table_name: str,
    records: Sequence[StepRecord | SnapshotRecord],
    bundle_id: UUID,
) -> None:
    """Lock archived rows and require each with its marker and owners.

    Args:
        session: Restore transaction.
        table_name: Table holding the rows.
        records: Archived records for that table.
        bundle_id: Marker each row must carry.

    Raises:
        ExecutionRetentionConflictError: A row is missing, marked by another
            bundle, or owned differently than when it was archived.
    """
    table = SQLModel.metadata.tables[table_name]
    expected = {record.id: record for record in records}
    found: Dict[UUID, Any] = {}
    for group in transactions.batches(expected):
        for locked in session.execute(
            select(table)
            .where(table.c.id.in_(group))
            .order_by(table.c.id)
            .with_for_update()
        ).mappings():
            found[locked["id"]] = locked
    for identity, record in expected.items():
        row = found.get(identity)
        if row is None or row["archive_bundle_id"] != bundle_id:
            raise ExecutionRetentionConflictError(
                "Restore needs every archived row with its archive marker."
            )
        owners = record.model_dump(
            include={"project_id", "pipeline_run_id", "snapshot_id"}
        )
        if any(row[column] != value for column, value in owners.items()):
            raise ExecutionRetentionConflictError(
                "An archived row changed its owner."
            )


def _require_free_configurations(
    session: Session, document: ArchiveDocument
) -> None:
    """Require that no configuration was recreated for the archived owners.

    Args:
        session: Restore transaction.
        document: Verified archive document.

    Raises:
        ExecutionRetentionConflictError: A configuration identity or owner is
            already occupied.
    """
    if not document.configurations:
        return
    owners = (
        (
            col(StepConfigurationSchema.id),
            [configuration.id for configuration in document.configurations],
        ),
        (
            col(StepConfigurationSchema.snapshot_id),
            [snapshot.id for snapshot in document.snapshots],
        ),
        (
            col(StepConfigurationSchema.step_run_id),
            [step.id for step in document.steps],
        ),
    )
    for column, identities in owners:
        for group in transactions.batches(identities):
            occupied = session.execute(
                select(col(StepConfigurationSchema.id))
                .where(column.in_(group))
                .limit(1)
            ).first()
            if occupied is not None:
                raise ExecutionRetentionConflictError(
                    "A restored configuration identity or owner is already "
                    "in use."
                )


def _write_back(
    session: Session, document: ArchiveDocument, bundle_id: UUID
) -> None:
    """Restore archived columns, clear markers, and insert configurations.

    Args:
        session: Restore transaction holding the row locks.
        document: Verified archive document.
        bundle_id: Marker being cleared.
    """
    connection = session.connection()
    connection.execute(
        update(PipelineRunSchema)
        .where(
            col(PipelineRunSchema.id) == document.run_id,
            col(PipelineRunSchema.archive_bundle_id) == bundle_id,
        )
        .values(**_archived_values(document.run), archive_bundle_id=None)
    )
    for table_name, records in (
        ("step_run", document.steps),
        ("pipeline_snapshot", document.snapshots),
    ):
        if not records:
            continue
        table = SQLModel.metadata.tables[table_name]
        columns = type(records[0]).archived_columns
        connection.execute(
            update(table)
            .where(table.c.id == bindparam("restored_id"))
            .values(
                archive_bundle_id=None,
                **{
                    column: bindparam(f"restored_{column}")
                    for column in columns
                },
            ),
            [
                {
                    "restored_id": record.id,
                    **{
                        f"restored_{column}": value
                        for column, value in _archived_values(record).items()
                    },
                }
                for record in records
            ],
        )
    if document.configurations:
        connection.execute(
            insert(StepConfigurationSchema),
            [
                _archived_values(configuration)
                for configuration in document.configurations
            ],
        )


def _archived_values(record: Record) -> Dict[str, Any]:
    """Return the columns a record writes back to SQL.

    Args:
        record: Verified archive record.

    Returns:
        Column values keyed by column name.
    """
    return record.model_dump(include=set(record.archived_columns))
