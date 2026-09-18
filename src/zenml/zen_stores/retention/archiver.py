# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Archiving one run at a time, on a schedule or on demand.

Every run travels the same path: capture, encode, upload, and read back byte
for byte before SQL changes. Retirement then runs in one transaction: it
locks the run, its steps, its owned snapshots, and their configurations,
captures the run again, and only proceeds if the document hash is unchanged.
It inserts the bundle row and sets the markers together, so the database
decides every race: two archivers racing on one run leave one bundle, and the
loser's object is removed.

``ArchivePass`` adds the scheduled sweep on top: one lease across all
replicas, a saved position, and counts. ``archive_runs`` is the targeted
form and needs no lease, because each run is still retired under its own row
locks. It follows normal policy unless the caller explicitly requests force.

Retirement deliberately does not refresh ``updated`` on the retired rows, so
their headers keep describing the execution rather than the archiving.
"""

from contextlib import contextmanager
from datetime import datetime
from threading import Event
from time import monotonic
from typing import (
    ClassVar,
    Iterator,
    List,
    Literal,
    Optional,
    Protocol,
    Sequence,
)
from uuid import UUID, uuid4

from pydantic import BaseModel
from sqlalchemy import Engine, bindparam, delete, select, update
from sqlmodel import Session, SQLModel, col

from zenml.config.server_config import ArchiveSettings
from zenml.enums import RetentionExclusion, RetentionFailure, RetentionOutcome
from zenml.exceptions import (
    ExecutionRetentionConflictError,
    ExecutionRetentionIntegrityError,
)
from zenml.logger import get_logger
from zenml.models.v2.misc.retention import (
    MAX_REFUSALS,
    ArchiveRefusal,
    ArchiveResponse,
)
from zenml.zen_stores.retention import transactions
from zenml.zen_stores.retention.capture import ProjectionCache, capture_run
from zenml.zen_stores.retention.eligibility import (
    ArchivableRun,
    discover_runs,
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
from zenml.zen_stores.retention.state import Cursor, RetentionState
from zenml.zen_stores.retention.storage import ArchiveStorage
from zenml.zen_stores.schemas import (
    ArchiveBundleSchema,
    PipelineRunSchema,
    PipelineSnapshotSchema,
    ServerSettingsSchema,
    StepConfigurationSchema,
    StepRunSchema,
)

logger = get_logger(__name__)

RunOutcome = Literal["archived", "skipped", "oversized", "failed"]

# Snapshot rows require these columns, so retirement stores empty objects.
EMPTY_JSON = canonical_json({}).decode()


class ArchiveAttempt(BaseModel):
    """How one run's archiving ended, and the reason if it was refused."""

    run_id: UUID
    outcome: RunOutcome
    exclusion: Optional[RetentionExclusion] = None


class RunCounts(Protocol):
    """The four per-run outcome counters, tallied the same way everywhere."""

    archived: int
    skipped: int
    oversized: int
    failed: int


def tally(counts: RunCounts, outcome: RunOutcome) -> None:
    """Count one attempt against a sweep's state or a targeted result.

    Args:
        counts: Counters to advance.
        outcome: How the attempt ended.
    """
    if outcome == "archived":
        counts.archived += 1
    elif outcome == "oversized":
        counts.oversized += 1
    elif outcome == "failed":
        counts.failed += 1
    else:
        counts.skipped += 1


class _PassReplaced(Exception):
    """Another sweep took over the saved state after its lease expired."""


class _RetentionCancelled(Exception):
    """Cooperative stop requested before another retirement starts."""


class _RetirementRolledBack(Exception):
    """Retirement body failed and its transaction rollback completed."""

    def __init__(self, error: Exception) -> None:
        """Keep the original error for outcome classification.

        Args:
            error: Error whose transaction was rolled back.
        """
        super().__init__(str(error))
        self.error = error


@contextmanager
def _retirement_transaction(engine: Engine) -> Iterator[Session]:
    """Expose positive rollback evidence without hiding commit ambiguity.

    Args:
        engine: Metadata database.

    Yields:
        Retirement session.

    Raises:
        _RetirementRolledBack: The transaction body failed and rollback was
            confirmed.
        Exception: The transaction outcome is unknown or rollback failed.
    """
    session: Optional[Session] = None
    try:
        with transactions.transaction(engine) as session:
            yield session
    except Exception as error:
        if session is not None and transactions.rollback_was_confirmed(
            session
        ):
            raise _RetirementRolledBack(error) from error
        raise


class RunArchiver:
    """Archives runs one at a time against one configured archive storage."""

    def __init__(
        self,
        engine: Engine,
        storage: ArchiveStorage,
        settings: ArchiveSettings,
        cancel_event: Optional[Event] = None,
    ) -> None:
        """Bind the database and storage without touching either.

        Args:
            engine: Metadata database.
            storage: Archive storage.
            settings: The server's archive settings.
            cancel_event: Cooperative cancellation signal for a sweep.
        """
        self.engine = engine
        self.storage = storage
        self.settings = settings
        self.cancel_event = cancel_event

    def _check_cancelled(self) -> None:
        """Stop before beginning another irreversible phase.

        Raises:
            _RetentionCancelled: If the owning sweep is shutting down.
        """
        if self.cancel_event is not None and self.cancel_event.is_set():
            raise _RetentionCancelled()

    def archive(
        self, run_id: UUID, evaluated_at: datetime, *, force: bool = False
    ) -> ArchiveAttempt:
        """Inspect one run and archive it when every rule allows it.

        Args:
            run_id: Candidate run.
            evaluated_at: Evaluation time shared by the whole batch.
            force: Ignore the age, model-link, and restore-grace rules.

        Returns:
            How the attempt ended, with a reason when the run was refused.

        Raises:
            _RetentionCancelled: The owning sweep is shutting down.
        """
        self._check_cancelled()
        try:
            with Session(self.engine) as session:
                run = inspect_run(
                    session, run_id, self.settings, evaluated_at, force=force
                )
            self._check_cancelled()
            if run.exclusion is RetentionExclusion.OVERSIZED:
                return ArchiveAttempt(
                    run_id=run_id, outcome="oversized", exclusion=run.exclusion
                )
            if run.exclusion is not None:
                return ArchiveAttempt(
                    run_id=run_id, outcome="skipped", exclusion=run.exclusion
                )
            return self._archive(run, evaluated_at, force)
        except _RetentionCancelled:
            raise
        except Exception as error:
            # SQL errors can contain archived payloads; log only their type.
            logger.error(
                "Archiving run %s failed (%s).", run_id, type(error).__name__
            )
            return ArchiveAttempt(run_id=run_id, outcome="failed")

    def _archive(
        self, run: ArchivableRun, evaluated_at: datetime, force: bool
    ) -> ArchiveAttempt:
        """Capture, upload, verify, and retire one eligible run.

        Args:
            run: Inspected, eligible run.
            evaluated_at: Evaluation time shared by the whole batch.
            force: Rule set to reapply under the retirement locks.

        Returns:
            How the attempt ended.

        Raises:
            ExecutionRetentionIntegrityError: The uploaded object does not
                match the capture; caught below and reported as a failure.
            _RetentionCancelled: The owning sweep is shutting down.
        """  # noqa: DOC502
        self._check_cancelled()
        # Filled outside the locks so retirement need not validate every
        # step configuration again while it blocks the run's writers.
        projections: ProjectionCache = {}
        try:
            with Session(self.engine) as session:
                encoded = encode(
                    capture_run(
                        session,
                        run,
                        check_cancelled=self._check_cancelled,
                        projections=projections,
                    )
                )
        except ExecutionRetentionConflictError as error:
            return self._conflict_attempt(run.run_id, error)
        self._check_cancelled()
        bundle_id = uuid4()
        uri = self.storage.object_uri(run.project, run.run_id, bundle_id)
        retirement_started = False
        object_written = False
        try:
            self.storage.write(uri, encoded.data)
            object_written = True
            self._check_cancelled()
            if self.storage.read(uri, len(encoded.data)) != encoded.data:
                raise ExecutionRetentionIntegrityError(
                    "Uploaded archive object differs from the capture."
                )
            self._check_cancelled()
            retirement_started = True
            self._retire(
                run, bundle_id, uri, encoded, evaluated_at, force, projections
            )
            return ArchiveAttempt(run_id=run.run_id, outcome="archived")
        except _RetentionCancelled:
            if object_written and not retirement_started:
                self.storage.remove(uri)
            raise
        except _RetirementRolledBack as failure:
            self.storage.remove(uri)
            cause = failure.error
            if isinstance(cause, ExecutionRetentionConflictError):
                return self._conflict_attempt(run.run_id, cause)
            if transactions.is_transient_lock_error(cause):
                return ArchiveAttempt(run_id=run.run_id, outcome="skipped")
            logger.error(
                "Archiving run %s failed (%s).",
                run.run_id,
                type(cause).__name__,
            )
            return ArchiveAttempt(run_id=run.run_id, outcome="failed")
        except ExecutionRetentionConflictError as error:
            if not retirement_started:
                self.storage.remove(uri)
            elif self._bundle_committed(bundle_id):
                return ArchiveAttempt(run_id=run.run_id, outcome="archived")
            return self._conflict_attempt(run.run_id, error)
        except Exception as error:
            if not retirement_started:
                self.storage.remove(uri)
            elif self._bundle_committed(bundle_id):
                # The commit succeeded but its acknowledgement was lost.
                return ArchiveAttempt(run_id=run.run_id, outcome="archived")
            logger.error(
                "Archiving run %s failed (%s).",
                run.run_id,
                type(error).__name__,
            )
            return ArchiveAttempt(run_id=run.run_id, outcome="failed")

    def _bundle_committed(self, bundle_id: UUID) -> bool:
        """Check only for positive evidence that retirement committed.

        A missing row is inconclusive while a failed commit may still be in
        progress on another connection. The caller therefore retains the
        object unless this lookup positively recovers a committed retirement.

        Args:
            bundle_id: Bundle row the retirement would have inserted.

        Returns:
            Whether the bundle row exists, so the run is archived.
        """
        try:
            with Session(self.engine) as session:
                committed = (
                    session.get(ArchiveBundleSchema, bundle_id) is not None
                )
        except Exception:
            return False
        return committed

    @staticmethod
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
        if error.error_code == RetentionFailure.OVERSIZED:
            return ArchiveAttempt(
                run_id=run_id,
                outcome="oversized",
                exclusion=RetentionExclusion.OVERSIZED,
            )
        return ArchiveAttempt(
            run_id=run_id,
            outcome="skipped",
            exclusion=RetentionExclusion.NOT_ELIGIBLE,
        )

    def _retire(
        self,
        run: ArchivableRun,
        bundle_id: UUID,
        uri: str,
        encoded: EncodedDocument,
        evaluated_at: datetime,
        force: bool,
        projections: ProjectionCache,
    ) -> None:
        """Replace the run's SQL detail with the verified bundle atomically.

        Args:
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
        with _retirement_transaction(self.engine) as session:
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
                self.settings,
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
                    | col(StepConfigurationSchema.snapshot_id).in_(
                        fresh.snapshot_ids
                    )
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
    owned by an active root stays in the database with its reason. No lease
    is taken: every run is retired under its own row locks, so a targeted
    archive and the scheduled sweep can only ever duplicate work, never
    corrupt each other.

    Args:
        engine: Metadata database.
        storage: Archive storage.
        settings: The server's archive settings.
        run_ids: Runs to archive, already authorized by the caller.
        force: Ignore age, model links, and restore grace while preserving all
            execution-safety exclusions.

    Returns:
        Counts and a capped list of the runs that were refused.
    """
    archiver = RunArchiver(engine, storage, settings)
    with Session(engine) as session:
        evaluated_at = transactions.database_now(session)
    result = ArchiveResponse()
    refusals: List[ArchiveRefusal] = []
    for run_id in run_ids:
        attempt = archiver.archive(run_id, evaluated_at, force=force)
        tally(result, attempt.outcome)
        if attempt.exclusion is not None:
            refusals.append(
                ArchiveRefusal(run_id=attempt.run_id, reason=attempt.exclusion)
            )
    result.refusals = refusals[:MAX_REFUSALS]
    result.refusals_truncated = len(refusals) > MAX_REFUSALS
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
        force: Ignore age, model links, and restore grace while preserving all
            execution-safety exclusions.

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
            outcome: RunOutcome = (
                "oversized"
                if run.exclusion == RetentionExclusion.OVERSIZED
                else "skipped"
            )
            tally(result, outcome)
            refusals.append(
                ArchiveRefusal(run_id=run_id, reason=run.exclusion)
            )
    result.refusals = refusals[:MAX_REFUSALS]
    result.refusals_truncated = len(refusals) > MAX_REFUSALS
    return result


class ArchivePass:
    """One bounded archive sweep over every project, oldest runs first.

    The sweep owns the lease, the saved position and the counts, and hands
    each candidate to a ``RunArchiver``. It deliberately does not inherit
    that archiver: forcing one arbitrary run past the age and model-link
    rules is not something a bounded sweep should be able to do.
    """

    MAX_SECONDS: ClassVar[int] = 60

    def __init__(
        self,
        engine: Engine,
        storage: ArchiveStorage,
        settings: ArchiveSettings,
        cancel_event: Optional[Event] = None,
    ) -> None:
        """Prepare a sweep without touching the database.

        Args:
            engine: Metadata database.
            storage: Archive storage.
            settings: The server's archive settings.
            cancel_event: Cooperative cancellation signal from the scheduler.
        """
        self.engine = engine
        self.storage = storage
        self.settings = settings
        self.cancel_event = cancel_event
        self.archiver = RunArchiver(
            engine, storage, settings, cancel_event=cancel_event
        )
        self.operation_id = uuid4()
        self.settings_id: Optional[UUID] = None
        self.state = RetentionState()

    def accept(self) -> None:
        """Take the server-wide sweep lease.

        Raises:
            ExecutionRetentionConflictError: Another replica is sweeping.
        """
        with transactions.transaction(self.engine) as session:
            self._load(session)
            now = transactions.database_now(session)
            if self.state.is_live(now):
                raise ExecutionRetentionConflictError(
                    "An archive sweep is already running on this server. "
                    "Retry after it finishes."
                )
            self.state.start(self.operation_id)
            self._save(session, now)

    def run(self) -> RetentionState:
        """Archive a bounded batch and record the outcome.

        The sweep must have taken the lease first.

        Returns:
            The saved state after the sweep.
        """
        started = monotonic()
        try:
            self._check_cancelled()
            if not self.storage.probe():
                return self._finish(
                    RetentionOutcome.FAILED,
                    RetentionFailure.STORAGE_CONFIGURATION,
                )
            with Session(self.engine) as session:
                evaluated_at = transactions.database_now(session)
                candidates = discover_runs(
                    session,
                    self.settings,
                    evaluated_at,
                    self.state.cursor,
                    self.settings.max_runs_per_pass + 1,
                    self.state.oversized_run_ids,
                )
            for cursor in candidates[: self.settings.max_runs_per_pass]:
                self._check_cancelled()
                if monotonic() - started >= self.MAX_SECONDS:
                    return self._finish(RetentionOutcome.PAUSED)
                self._process(cursor, evaluated_at)
            return self._finish(
                RetentionOutcome.SUCCEEDED
                if len(candidates) <= self.settings.max_runs_per_pass
                else RetentionOutcome.PAUSED
            )
        except _RetentionCancelled:
            return self._finish(RetentionOutcome.PAUSED)
        except _PassReplaced:
            return self.state
        except Exception as error:
            # SQL errors can contain archived payloads; log only their type.
            logger.error(
                "Archive sweep failed (%s).",
                type(error).__name__,
            )
            return self._finish(
                RetentionOutcome.FAILED, RetentionFailure.ARCHIVE_FAILED
            )

    def _check_cancelled(self) -> None:
        """Stop the pass before beginning more payload work.

        Raises:
            _RetentionCancelled: If scheduler shutdown was requested.
        """
        if self.cancel_event is not None and self.cancel_event.is_set():
            raise _RetentionCancelled()

    def _process(self, cursor: Cursor, evaluated_at: datetime) -> None:
        """Archive or skip one run and save the position after it.

        Args:
            cursor: Run to examine.
            evaluated_at: Evaluation time shared by the whole sweep.
        """
        attempt = self.archiver.archive(cursor.run_id, evaluated_at)
        with self._update() as state:
            state.cursor = cursor
            tally(state, attempt.outcome)
            if attempt.outcome == "oversized":
                # Runs over the byte budget are only found by reading them.
                state.remember_oversized(attempt.run_id)

    def _load(self, session: Session) -> None:
        """Lock the settings row while changing the latest sweep state.

        This lock is held only for progress updates, never during capture,
        storage I/O, or retirement. The operation ID still prevents a replaced
        worker from publishing progress.

        Args:
            session: Current short progress transaction.
        """
        row = session.execute(
            select(
                col(ServerSettingsSchema.id),
                col(ServerSettingsSchema.retention_state),
            ).with_for_update()
        ).one()
        self.settings_id = row.id
        self.state = RetentionState.load(row.retention_state)

    def _save(self, session: Session, now: datetime) -> None:
        """Save progress while holding the settings row lock.

        The statement writes only ``retention_state``, so sweep progress
        never looks like a settings change to clients watching ``updated``.

        Args:
            session: Transaction that locked and loaded the settings row.
            now: Current database time for the lease and finish timestamp.
        """
        active = self.state.last_outcome == RetentionOutcome.RUNNING
        self.state.operation_expires_at = (
            now + RetentionState.LEASE if active else None
        )
        self.state.last_finished_at = None if active else now
        session.execute(
            update(ServerSettingsSchema)
            .where(col(ServerSettingsSchema.id) == self.settings_id)
            .values(retention_state=self.state.model_dump_json())
        )

    @contextmanager
    def _update(self) -> Iterator[RetentionState]:
        """Change progress only while this sweep still owns it.

        Yields:
            Locked state to update before committing the short transaction.

        Raises:
            _PassReplaced: Another sweep took over the state.
        """
        with transactions.transaction(self.engine) as session:
            self._load(session)
            if self.state.operation_id != self.operation_id:
                raise _PassReplaced()
            yield self.state
            self._save(session, transactions.database_now(session))

    def _finish(
        self,
        outcome: RetentionOutcome,
        failure: Optional[RetentionFailure] = None,
    ) -> RetentionState:
        """Record the sweep outcome unless another sweep took over.

        Args:
            outcome: Final outcome.
            failure: Safe failure classification for the server logs.

        Returns:
            The saved state.
        """
        try:
            with self._update() as state:
                state.last_outcome = outcome
                if outcome == RetentionOutcome.SUCCEEDED:
                    state.cursor = None
        except _PassReplaced:
            pass
        if failure is not None:
            logger.warning("Archive sweep failed (%s).", failure)
        return self.state


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
