# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Archiving selected runs one at a time.

Every run travels the same path: capture, encode, upload, and read back byte
for byte before SQL changes. Retirement then runs in one transaction: it
locks the run, its steps, its owned snapshots, and their configurations,
captures the run again, and only proceeds if the document hash is unchanged.
It inserts the bundle row and sets the markers together, so the database
decides every race: two archivers racing on one run leave one bundle, and the
loser's object is removed.

Concurrent requests for the same run can only duplicate work, because each
run is retired under its own row locks. Normal policy applies unless the
caller requests force.

Retirement deliberately does not refresh ``updated`` on the retired rows, so
their headers keep describing the execution rather than the archiving.
"""

from datetime import datetime
from typing import List, Literal, Optional, Sequence
from uuid import UUID, uuid4

from pydantic import BaseModel
from sqlalchemy import Engine, bindparam, delete, select, update
from sqlmodel import Session, SQLModel, col

from zenml.config.server_config import ArchiveSettings
from zenml.enums import RetentionExclusion
from zenml.exceptions import (
    ExecutionRetentionConflictError,
    ExecutionRetentionIntegrityError,
    ExecutionRetentionOversizedError,
)
from zenml.logger import get_logger
from zenml.models.v2.misc.retention import (
    ArchiveRefusal,
    ArchiveResponse,
)
from zenml.zen_stores.retention import transactions
from zenml.zen_stores.retention.capture import ProjectionCache, capture_run
from zenml.zen_stores.retention.eligibility import (
    ArchivableRun,
    inspect_run,
)
from zenml.zen_stores.retention.format import (
    FORMAT_VERSION,
    ArchiveDocument,
    EncodedDocument,
    canonical_json,
    compute_content_hash,
    encode,
)
from zenml.zen_stores.retention.storage import ArchiveStorage
from zenml.zen_stores.schemas import (
    ArchiveBundleSchema,
    PipelineRunSchema,
    PipelineSnapshotSchema,
    StepConfigurationSchema,
    StepRunSchema,
)

logger = get_logger(__name__)

# Bound the refusal list persisted with each API transaction result.
MAX_REFUSALS = 100


RunOutcome = Literal["archived", "skipped", "oversized", "failed"]

# Snapshot rows require these columns, so retirement stores empty objects.
EMPTY_JSON = canonical_json({}).decode()


class ArchiveAttempt(BaseModel):
    """How one run's archiving ended, and the reason if it was refused."""

    run_id: UUID
    outcome: RunOutcome
    exclusion: Optional[RetentionExclusion] = None


def archive_runs(
    engine: Engine,
    storage: ArchiveStorage,
    settings: ArchiveSettings,
    run_ids: Sequence[UUID],
    *,
    force: bool = False,
) -> ArchiveResponse:
    """Archive named runs now under normal policy or an explicit override.

    The safety rules still apply, so a run that is unfinished, resumable, or
    owned by an active root stays in the database with its reason.

    Args:
        engine: Metadata database.
        storage: Archive storage.
        settings: The server's archive settings.
        run_ids: Runs to archive, already authorized by the caller.
        force: Ignore the minimum age while preserving all execution-safety
            exclusions.

    Returns:
        Counts and a capped list of the runs that were refused.
    """
    with Session(engine) as session:
        evaluated_at = transactions.database_now(session)
    result = ArchiveResponse()
    refusals: List[ArchiveRefusal] = []
    for run_id in run_ids:
        try:
            attempt = _archive_run(
                engine, storage, settings, run_id, evaluated_at, force=force
            )
        except Exception as error:
            attempt = _failed_attempt(run_id, error)
        _tally(result, attempt.outcome)
        if attempt.exclusion is not None:
            refusals.append(
                ArchiveRefusal(run_id=attempt.run_id, reason=attempt.exclusion)
            )
    _record_refusals(result, refusals)
    return result


def preview_runs(
    engine: Engine,
    settings: ArchiveSettings,
    run_ids: Sequence[UUID],
    *,
    force: bool = False,
) -> ArchiveResponse:
    """Inspect a bounded set without reading objects or changing state.

    Args:
        engine: Metadata database.
        settings: The server's archive settings.
        run_ids: Runs to inspect, already authorized by the caller.
        force: Ignore the minimum age while preserving all execution-safety
            exclusions.

    Returns:
        Eligible and excluded counts with a capped refusal list.
    """
    result = ArchiveResponse(dry_run=True)
    refusals: List[ArchiveRefusal] = []
    with Session(engine) as session:
        evaluated_at = transactions.database_now(session)
        for run_id in run_ids:
            try:
                run = inspect_run(
                    session, run_id, settings, evaluated_at, force=force
                )
            except Exception as error:
                logger.error(
                    "Previewing run %s failed (%s).",
                    run_id,
                    type(error).__name__,
                )
                result.failed += 1
                continue
            if run.exclusion is None:
                result.eligible += 1
                continue
            _tally(result, _refused_outcome(run.exclusion))
            refusals.append(
                ArchiveRefusal(run_id=run_id, reason=run.exclusion)
            )
    _record_refusals(result, refusals)
    return result


def _archive_run(
    engine: Engine,
    storage: ArchiveStorage,
    settings: ArchiveSettings,
    run_id: UUID,
    evaluated_at: datetime,
    *,
    force: bool = False,
) -> ArchiveAttempt:
    """Inspect, capture, verify the upload, and retire one run's SQL detail.

    Args:
        engine: Metadata database.
        storage: Archive storage.
        settings: The server's archive settings.
        run_id: Candidate run.
        evaluated_at: Evaluation time shared by the whole batch.
        force: Ignore the minimum-age rule in both eligibility checks.

    Returns:
        How the attempt ended, with a reason when the run was refused.

    Raises:
        ExecutionRetentionIntegrityError: The uploaded object differs from
            the capture; caught below and reported as a failure.
    """  # noqa: DOC502
    with Session(engine) as session:
        run = inspect_run(session, run_id, settings, evaluated_at, force=force)
    if run.exclusion is not None:
        return ArchiveAttempt(
            run_id=run_id,
            outcome=_refused_outcome(run.exclusion),
            exclusion=run.exclusion,
        )
    # Cache projections before taking locks to avoid repeating configuration
    # validation while blocking writers. Recapture still checks their inputs.
    projections: ProjectionCache = {}
    try:
        with Session(engine) as session:
            encoded = encode(
                capture_run(session, run, projections=projections)
            )
    except ExecutionRetentionConflictError as error:
        return _conflict_attempt(run_id, error)
    # Each attempt owns a unique object, so a losing archiver cannot delete a
    # concurrent winner's data. A crash before commit may leave an orphan.
    bundle_id = uuid4()
    uri = storage.object_uri(run.project, run_id, bundle_id)
    retirement_started = False
    retirement_session: Optional[Session] = None
    try:
        storage.write(uri, encoded.data)
        if storage.read(uri, len(encoded.data)) != encoded.data:
            raise ExecutionRetentionIntegrityError(
                "Uploaded archive object differs from the capture."
            )
        retirement_started = True
        with transactions.transaction(engine) as retirement_session:
            _retire_run(
                retirement_session,
                settings,
                run,
                bundle_id,
                uri,
                encoded,
                evaluated_at,
                force,
                projections,
            )
        return ArchiveAttempt(run_id=run_id, outcome="archived")
    except Exception as error:
        rolled_back = (
            retirement_session is not None
            and transactions.rollback_was_confirmed(retirement_session)
        )
        # An uncertain commit requires keeping the object even without a row.
        if not retirement_started or rolled_back:
            storage.remove(uri)
        elif _bundle_committed(engine, bundle_id):
            # The commit succeeded but its acknowledgement was lost.
            return ArchiveAttempt(run_id=run_id, outcome="archived")
        if isinstance(error, ExecutionRetentionConflictError):
            return _conflict_attempt(run_id, error)
        if rolled_back and transactions.is_transient_lock_error(error):
            return ArchiveAttempt(run_id=run_id, outcome="skipped")
        return _failed_attempt(run_id, error)


def _retire_run(
    session: Session,
    settings: ArchiveSettings,
    run: ArchivableRun,
    bundle_id: UUID,
    uri: str,
    encoded: EncodedDocument,
    evaluated_at: datetime,
    force: bool,
    projections: ProjectionCache,
) -> None:
    """Recheck the capture under row locks, then replace its SQL detail.

    Args:
        session: Retirement transaction owned by the archive operation.
        settings: The server's archive settings.
        run: Run inspected before capture.
        bundle_id: Identity of the uploaded object's bundle row.
        uri: Uploaded object.
        encoded: Uploaded bytes and their content hash.
        evaluated_at: Evaluation time shared by the whole batch.
        force: Rule set the run was inspected under.
        projections: Step projections derived by the first capture.

    Raises:
        ExecutionRetentionConflictError: The run changed or became
            ineligible after capture.
    """
    # Lock order shared with restore and writers: the run, its steps,
    # every snapshot they reference, then configurations. Ownership
    # is inspected only after the snapshot locks, so a new run that
    # starts using a snapshot is visible here or blocked until after.
    locked = session.execute(
        select(
            col(PipelineRunSchema.project_id),
            col(PipelineRunSchema.snapshot_id),
            col(PipelineRunSchema.archive_bundle_id),
        )
        .where(col(PipelineRunSchema.id) == run.run_id)
        .with_for_update()
    ).one_or_none()
    if (
        locked is None
        or locked.project_id != run.project
        or locked.archive_bundle_id is not None
    ):
        raise ExecutionRetentionConflictError(
            "Run disappeared or was archived after capture."
        )
    step_snapshots = session.execute(
        select(col(StepRunSchema.snapshot_id))
        .where(col(StepRunSchema.pipeline_run_id) == run.run_id)
        .order_by(col(StepRunSchema.id))
        .with_for_update()
    ).scalars()
    referenced = {
        snapshot_id
        for snapshot_id in [locked.snapshot_id, *step_snapshots]
        if snapshot_id is not None
    }
    transactions.lock_ids(session, PipelineSnapshotSchema, referenced)
    fresh = inspect_run(
        session,
        run.run_id,
        settings,
        evaluated_at,
        force=force,
    )
    if fresh.exclusion is not None:
        raise ExecutionRetentionConflictError(
            f"Run became ineligible after capture ({fresh.exclusion})."
        )
    session.execute(
        select(col(StepConfigurationSchema.id))
        .where(
            col(StepConfigurationSchema.step_run_id).in_(
                select(col(StepRunSchema.id)).where(
                    col(StepRunSchema.pipeline_run_id) == run.run_id
                )
            )
            | col(StepConfigurationSchema.snapshot_id).in_(fresh.snapshot_ids)
        )
        .order_by(col(StepConfigurationSchema.id))
        .with_for_update()
    ).all()
    document = capture_run(session, fresh, projections=projections)
    if compute_content_hash(document) != encoded.content_hash:
        raise ExecutionRetentionConflictError(
            "Run detail changed after capture."
        )
    session.add(
        ArchiveBundleSchema(
            id=bundle_id,
            project_id=run.project,
            run_id=run.run_id,
            uri=uri,
            size_bytes=len(encoded.data),
            content_hash=encoded.content_hash,
            format_version=FORMAT_VERSION,
        )
    )
    session.flush()
    _clear_detail(session, document, bundle_id)


def _clear_detail(
    session: Session, document: ArchiveDocument, bundle_id: UUID
) -> None:
    """Clear archived columns, delete configurations, and set markers.

    Args:
        session: Retirement transaction holding the run's row locks.
        document: Detail captured under those locks.
        bundle_id: Bundle row inserted in the same transaction.

    Raises:
        ExecutionRetentionConflictError: A locked row changed unexpectedly.
    """
    connection = session.connection()
    run_cleared = connection.execute(
        update(PipelineRunSchema)
        .where(
            col(PipelineRunSchema.id) == document.run_id,
            col(PipelineRunSchema.archive_bundle_id).is_(None),
        )
        .values(
            orchestrator_environment=None,
            exception_info=None,
            pipeline_configuration=None,
            client_environment=None,
            archive_bundle_id=bundle_id,
        )
    ).rowcount
    if run_cleared != 1:
        raise ExecutionRetentionConflictError("Run changed during retirement.")
    if document.steps:
        steps = SQLModel.metadata.tables[StepRunSchema.__tablename__]
        connection.execute(
            update(steps)
            .where(steps.c.id == bindparam("step_id"))
            .values(
                exception_info=None,
                step_configuration=None,
                source_code=None,
                docstring=None,
                archive_bundle_id=bundle_id,
                step_type=bindparam("projected_type"),
                substitutions=bindparam("projected_substitutions"),
            ),
            [
                {
                    "step_id": step.id,
                    "projected_type": step.step_type,
                    "projected_substitutions": canonical_json(
                        step.substitutions
                    ).decode(),
                }
                for step in document.steps
            ],
        )
    snapshot_ids = [snapshot.id for snapshot in document.snapshots]
    if snapshot_ids:
        cleared = connection.execute(
            update(PipelineSnapshotSchema)
            .where(
                col(PipelineSnapshotSchema.id).in_(snapshot_ids),
                col(PipelineSnapshotSchema.archive_bundle_id).is_(None),
            )
            .values(
                pipeline_configuration=EMPTY_JSON,
                client_environment=EMPTY_JSON,
                pipeline_spec=None,
                source_code=None,
                description=None,
                archive_bundle_id=bundle_id,
            )
        ).rowcount
        if cleared != len(snapshot_ids):
            raise ExecutionRetentionConflictError(
                "Snapshot changed during retirement."
            )
    configuration_ids = [
        configuration.id for configuration in document.configurations
    ]
    for group in transactions.batches(configuration_ids):
        connection.execute(
            delete(StepConfigurationSchema).where(
                col(StepConfigurationSchema.id).in_(group)
            )
        )


def _bundle_committed(engine: Engine, bundle_id: UUID) -> bool:
    """Check only for positive evidence that retirement committed.

    A missing row is inconclusive while a failed commit may still be in
    progress on another connection. The caller therefore retains the
    object unless this lookup positively recovers a committed retirement.

    Args:
        engine: Metadata database.
        bundle_id: Bundle row the retirement would have inserted.

    Returns:
        Whether the bundle row exists, so the run is archived.
    """
    try:
        with Session(engine) as session:
            committed = session.get(ArchiveBundleSchema, bundle_id) is not None
    except Exception:
        return False
    return committed


def _conflict_attempt(
    run_id: UUID, error: ExecutionRetentionConflictError
) -> ArchiveAttempt:
    """Classify a run that could not be archived as captured.

    Args:
        run_id: Run that conflicted.
        error: Conflict raised by capture or retirement.

    Returns:
        Oversized when the run exceeds a limit, otherwise skipped; a
        changed run is reconsidered by a later attempt.
    """
    exclusion = (
        RetentionExclusion.OVERSIZED
        if isinstance(error, ExecutionRetentionOversizedError)
        else RetentionExclusion.NOT_ELIGIBLE
    )
    return ArchiveAttempt(
        run_id=run_id,
        outcome=_refused_outcome(exclusion),
        exclusion=exclusion,
    )


def _tally(result: ArchiveResponse, outcome: RunOutcome) -> None:
    """Count one attempt against the archive result.

    Args:
        result: Counters to advance.
        outcome: How the attempt ended.
    """
    if outcome == "archived":
        result.archived += 1
    elif outcome == "oversized":
        result.oversized += 1
    elif outcome == "failed":
        result.failed += 1
    else:
        result.skipped += 1


def _record_refusals(
    result: ArchiveResponse, refusals: List[ArchiveRefusal]
) -> None:
    """Attach a capped list of refused runs to the result.

    Args:
        result: Result to complete.
        refusals: Every refused run, in attempt order.
    """
    result.refusals = refusals[:MAX_REFUSALS]
    result.refusals_truncated = len(refusals) > MAX_REFUSALS


def _failed_attempt(run_id: UUID, error: BaseException) -> ArchiveAttempt:
    """Log a failed attempt and report it as failed.

    Args:
        run_id: Run whose archiving failed.
        error: The failure.

    Returns:
        A failed attempt.
    """
    # SQL errors can contain archived payloads; log only their type.
    logger.error("Archiving run %s failed (%s).", run_id, type(error).__name__)
    return ArchiveAttempt(run_id=run_id, outcome="failed")


def _refused_outcome(exclusion: RetentionExclusion) -> RunOutcome:
    """Count an oversized run separately from every other refusal.

    Args:
        exclusion: Why the run was not archived.

    Returns:
        The outcome the refusal is tallied under.
    """
    return (
        "oversized" if exclusion == RetentionExclusion.OVERSIZED else "skipped"
    )
