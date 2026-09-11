# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Bounded archive passes and atomic retirement of verified run detail.

A pass examines up to ``max_runs_per_pass`` runs from the project's saved
position, for at most ``MAX_SECONDS``. Each eligible run is captured, encoded,
uploaded, and read back byte for byte before SQL changes. Retirement then
runs in one transaction: it locks the run, its steps, its owned snapshots,
and their configurations, captures the run again, and only proceeds if the
document hash is unchanged. It inserts the bundle row and sets the markers
together, so the database decides every race: two passes racing on one run
leave one bundle, and the loser's object is removed.

Retirement deliberately does not refresh ``updated`` on the retired rows, so
their headers keep describing the execution rather than the archiving.
"""

from datetime import datetime
from time import monotonic
from typing import Callable, ClassVar, Literal, Optional
from uuid import UUID, uuid4

from sqlalchemy import Engine, bindparam, delete, select, update
from sqlmodel import Session, SQLModel, col

from zenml.enums import RetentionExclusion, RetentionFailure, RetentionOutcome
from zenml.exceptions import (
    ExecutionRetentionConflictError,
    ExecutionRetentionIntegrityError,
    IllegalOperationError,
)
from zenml.logger import get_logger
from zenml.models.v2.misc.retention import RetentionSettings
from zenml.zen_stores.retention import transactions
from zenml.zen_stores.retention.capture import capture_run
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
    encode,
)
from zenml.zen_stores.retention.state import Cursor, RetentionState
from zenml.zen_stores.retention.storage import ArchiveStorage
from zenml.zen_stores.schemas import (
    ArchiveBundleSchema,
    PipelineRunSchema,
    PipelineSnapshotSchema,
    ProjectSchema,
    StepConfigurationSchema,
    StepRunSchema,
)

logger = get_logger(__name__)

RunOutcome = Literal["archived", "skipped", "oversized", "failed"]

# Snapshot rows require these columns, so retirement stores empty objects.
EMPTY_JSON = canonical_json({}).decode()


class _PassReplaced(Exception):
    """Another pass took over this project's state after its lease expired."""


class _PolicyChanged(Exception):
    """The project's saved policy changed after this pass accepted it."""


class ArchivePass:
    """One bounded archive pass over a project."""

    MAX_SECONDS: ClassVar[int] = 60

    def __init__(
        self,
        engine: Engine,
        storage: ArchiveStorage,
        project_id: UUID,
        policy: RetentionSettings,
    ) -> None:
        """Bind an enabled policy without touching the database.

        Args:
            engine: Metadata database.
            storage: Archive storage.
            project_id: Authorized project.
            policy: Saved project policy for this pass.

        Raises:
            IllegalOperationError: The project has no archive age configured.
        """
        if policy.archive_after_days is None:
            raise IllegalOperationError(
                "Execution retention is disabled for this project."
            )
        self.engine = engine
        self.storage = storage
        self.project_id = project_id
        self.policy = policy.model_copy(deep=True)
        self.operation_id = uuid4()
        self.state = RetentionState()
        self.state_raw: Optional[str] = None

    def accept(self) -> None:
        """Take over the project's pass state for this pass.

        Raises:
            ExecutionRetentionConflictError: The policy changed, or another
                pass still holds the lease.
        """
        with transactions.transaction(self.engine) as session:
            saved_raw = self._load(session)
            if not self._policy_matches(saved_raw):
                raise ExecutionRetentionConflictError(
                    "The retention policy changed before the pass started."
                )
            now = transactions.database_now(session)
            if self.state.is_live(now):
                raise ExecutionRetentionConflictError(
                    "An archive pass is already running for this project. "
                    "Retry after it finishes."
                )
            self.state.start(self.operation_id)
            self._save(session, now)

    def abort(self, error_code: RetentionFailure) -> None:
        """Record a pass that failed before it started.

        Args:
            error_code: Safe failure classification.
        """
        self._finish(RetentionOutcome.FAILED, error_code)

    def run(self) -> RetentionState:
        """Archive a bounded batch and record the outcome.

        The pass must have been accepted first.

        Returns:
            The saved state after the pass.
        """
        started = monotonic()
        try:
            self._update(self._mark_running)
            if not self.storage.probe():
                return self._finish(
                    RetentionOutcome.FAILED,
                    RetentionFailure.STORAGE_CONFIGURATION,
                )
            with Session(self.engine) as session:
                evaluated_at = transactions.database_now(session)
                candidates = discover_runs(
                    session,
                    self.project_id,
                    self.policy,
                    evaluated_at,
                    self.state.cursor,
                    self.policy.max_runs_per_pass + 1,
                    self.state.oversized_run_ids,
                )
            for cursor in candidates[: self.policy.max_runs_per_pass]:
                if monotonic() - started >= self.MAX_SECONDS:
                    return self._finish(RetentionOutcome.PAUSED)
                self._process(cursor, evaluated_at)
            return self._finish(
                RetentionOutcome.SUCCEEDED
                if len(candidates) <= self.policy.max_runs_per_pass
                else RetentionOutcome.PAUSED
            )
        except _PassReplaced:
            return self.state
        except _PolicyChanged:
            return self._finish(RetentionOutcome.PAUSED)
        except Exception as error:
            # SQL errors can contain archived payloads; log only their type.
            logger.error(
                "Retention pass for project %s failed (%s).",
                self.project_id,
                type(error).__name__,
            )
            return self._finish(
                RetentionOutcome.FAILED, RetentionFailure.ARCHIVE_FAILED
            )

    @staticmethod
    def _mark_running(state: RetentionState, now: datetime) -> None:
        """Record that the accepted pass started working.

        Args:
            state: Saved state owned by this pass.
            now: Current database time.
        """
        state.last_outcome = RetentionOutcome.RUNNING

    def _process(self, cursor: Cursor, evaluated_at: datetime) -> None:
        """Archive or skip one run and save the position after it.

        Args:
            cursor: Run to examine.
            evaluated_at: Evaluation time shared by the whole pass.
        """
        with Session(self.engine) as session:
            run = inspect_run(
                session,
                self.project_id,
                cursor.run_id,
                self.policy,
                evaluated_at,
            )
        outcome: RunOutcome
        if run.exclusion == RetentionExclusion.OVERSIZED:
            outcome = "oversized"
        elif run.exclusion is not None:
            outcome = "skipped"
        else:
            outcome = self._archive(run, evaluated_at)

        def record(state: RetentionState, now: datetime) -> None:
            state.cursor = cursor
            if outcome == "archived":
                state.archived += 1
            elif outcome == "oversized":
                state.oversized += 1
                if run.exclusion is None:
                    # Found only by reading the run; skip it in later scans.
                    state.remember_oversized(run.run_id)
            elif outcome == "failed":
                state.failed += 1
            else:
                state.skipped += 1

        self._update(record)

    def _archive(
        self, run: ArchivableRun, evaluated_at: datetime
    ) -> RunOutcome:
        """Capture, upload, verify, and retire one eligible run.

        Args:
            run: Inspected, eligible run.
            evaluated_at: Evaluation time shared by the whole pass.

        Returns:
            How the attempt ended.

        Raises:
            _PolicyChanged: The saved policy changed during retirement.
        """  # noqa: DOC503
        try:
            with Session(self.engine) as session:
                encoded = encode(capture_run(session, run))
        except ExecutionRetentionConflictError as error:
            return self._conflict_outcome(error)
        bundle_id = uuid4()
        uri = self.storage.object_uri(self.project_id, run.run_id, bundle_id)
        try:
            self.storage.write(uri, encoded.data)
            if self.storage.read(uri, len(encoded.data)) != encoded.data:
                raise ExecutionRetentionIntegrityError(
                    "Uploaded archive object differs from the capture."
                )
            self._retire(run, bundle_id, uri, encoded, evaluated_at)
            return "archived"
        except _PolicyChanged:
            self._discard(bundle_id, uri)
            raise
        except ExecutionRetentionConflictError as error:
            self._discard(bundle_id, uri)
            return self._conflict_outcome(error)
        except Exception as error:
            if self._discard(bundle_id, uri):
                # The commit succeeded but its acknowledgement was lost.
                return "archived"
            if transactions.is_transient_lock_error(error):
                return "skipped"
            logger.error(
                "Archiving run %s failed (%s).",
                run.run_id,
                type(error).__name__,
            )
            return "failed"

    def _discard(self, bundle_id: UUID, uri: str) -> bool:
        """Remove an uploaded object unless its bundle row committed.

        A failed commit acknowledgement can hide a successful retirement, so
        the bundle row decides. When the database cannot answer, the object
        stays: an unreferenced object is harmless, a deleted referenced one
        loses data.

        Args:
            bundle_id: Bundle row the retirement would have inserted.
            uri: Uploaded object.

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
        if not committed:
            self.storage.remove(uri)
        return committed

    @staticmethod
    def _conflict_outcome(
        error: ExecutionRetentionConflictError,
    ) -> RunOutcome:
        """Classify a run that could not be archived as-is.

        Args:
            error: Conflict raised by capture or retirement.

        Returns:
            Oversized when the run exceeds a limit, otherwise skipped; a
            changed run is reconsidered by a later pass.
        """
        if error.error_code == RetentionFailure.OVERSIZED:
            return "oversized"
        return "skipped"

    def _retire(
        self,
        run: ArchivableRun,
        bundle_id: UUID,
        uri: str,
        encoded: EncodedDocument,
        evaluated_at: datetime,
    ) -> None:
        """Replace the run's SQL detail with the verified bundle atomically.

        Args:
            run: Run inspected before capture.
            bundle_id: Identity of the uploaded object's bundle row.
            uri: Uploaded object.
            encoded: Uploaded bytes and their content hash.
            evaluated_at: Evaluation time shared by the whole pass.

        Raises:
            ExecutionRetentionConflictError: The run changed or became
                ineligible after capture.
            _PolicyChanged: The saved policy changed after acceptance.
        """
        with transactions.transaction(self.engine) as session:
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
                or locked.project_id != self.project_id
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
            saved_raw = session.execute(
                select(col(ProjectSchema.retention_settings)).where(
                    col(ProjectSchema.id) == self.project_id
                )
            ).scalar_one()
            if not self._policy_matches(saved_raw):
                raise _PolicyChanged()
            fresh = inspect_run(
                session,
                self.project_id,
                run.run_id,
                self.policy,
                evaluated_at,
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
            document = capture_run(session, fresh)
            if encode(document).content_hash != encoded.content_hash:
                raise ExecutionRetentionConflictError(
                    "Run detail changed after capture."
                )
            session.add(
                ArchiveBundleSchema(
                    id=bundle_id,
                    project_id=self.project_id,
                    run_id=run.run_id,
                    uri=uri,
                    size_bytes=len(encoded.data),
                    content_hash=encoded.content_hash,
                    format_version=FORMAT_VERSION,
                )
            )
            session.flush()
            _clear_detail(session, document, bundle_id)

    def _policy_matches(self, saved_raw: Optional[str]) -> bool:
        """Tell whether the saved policy is still the one this pass accepted.

        Args:
            saved_raw: Serialized policy read from the project row.

        Returns:
            True when the saved policy equals this pass's policy.
        """
        return RetentionSettings.load(saved_raw) == self.policy

    def _load(self, session: Session) -> Optional[str]:
        """Read the project's saved state and policy.

        Args:
            session: Current transaction.

        Returns:
            The serialized saved policy.
        """
        project = session.execute(
            select(
                col(ProjectSchema.retention_state),
                col(ProjectSchema.retention_settings),
            ).where(col(ProjectSchema.id) == self.project_id)
        ).one()
        self.state_raw = project.retention_state
        self.state = RetentionState.load(self.state_raw)
        saved_policy: Optional[str] = project.retention_settings
        return saved_policy

    def _save(self, session: Session, now: datetime) -> None:
        """Replace the saved state if nobody changed it since it was read.

        Args:
            session: Current transaction.
            now: Current database time, used for the pass lease.

        Raises:
            ExecutionRetentionConflictError: The saved state changed.
        """
        self.state.operation_expires_at = (
            now + RetentionState.LEASE
            if self.state.last_outcome in RetentionState.ACTIVE_OUTCOMES
            else None
        )
        serialized = self.state.model_dump_json()
        expected = col(ProjectSchema.retention_state)
        statement = (
            update(ProjectSchema)
            .where(
                col(ProjectSchema.id) == self.project_id,
                expected.is_(None)
                if self.state_raw is None
                else expected == self.state_raw,
            )
            .values(retention_state=serialized)
        )
        if session.connection().execute(statement).rowcount != 1:
            raise ExecutionRetentionConflictError(
                "The project's retention state changed during the pass."
            )
        self.state_raw = serialized

    def _update(
        self,
        apply: Callable[[RetentionState, datetime], None],
        *,
        require_policy: bool = True,
    ) -> None:
        """Apply a change to the saved state this pass still owns.

        Args:
            apply: Change to the freshly read state, given the database
                time.
            require_policy: Stop the pass if the saved policy changed.

        Raises:
            _PassReplaced: Another pass took over the state.
            _PolicyChanged: The saved policy changed.
        """
        with transactions.transaction(self.engine) as session:
            saved_raw = self._load(session)
            if self.state.operation_id != self.operation_id:
                raise _PassReplaced()
            if require_policy and not self._policy_matches(saved_raw):
                raise _PolicyChanged()
            now = transactions.database_now(session)
            apply(self.state, now)
            self._save(session, now)

    def _finish(
        self,
        outcome: RetentionOutcome,
        failure: Optional[RetentionFailure] = None,
    ) -> RetentionState:
        """Record the pass outcome unless another pass took over.

        Args:
            outcome: Final outcome.
            failure: Safe failure classification for the server logs.

        Returns:
            The saved state.
        """

        def finish(state: RetentionState, now: datetime) -> None:
            state.last_outcome = outcome
            state.last_finished_at = now
            if outcome == RetentionOutcome.SUCCEEDED:
                state.cursor = None

        try:
            self._update(finish, require_policy=False)
        except _PassReplaced:
            pass
        if failure is not None:
            logger.warning(
                "Retention pass for project %s failed (%s).",
                self.project_id,
                failure,
            )
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
