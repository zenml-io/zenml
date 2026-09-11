# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Bounded archive passes and atomic retirement of verified execution detail.

Retirement deliberately does not refresh row ``updated`` timestamps because
the locked recapture fingerprint uses them to detect concurrent changes.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from shutil import copyfileobj
from tempfile import TemporaryDirectory
from time import monotonic
from typing import Any, ClassVar, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Engine, LargeBinary, cast, delete, or_, select, update
from sqlmodel import Session, col

from zenml.artifact_stores.base_artifact_store import BaseArtifactStore
from zenml.config.server_config import ServerConfiguration
from zenml.enums import ArchiveBundleStatus, RetentionFailure, RetentionOutcome
from zenml.exceptions import (
    ExecutionRetentionConflictError,
    ExecutionRetentionIntegrityError,
    IllegalOperationError,
)
from zenml.logger import get_logger
from zenml.models.v2.misc.retention import RetentionSettings
from zenml.zen_stores.retention import claims, transactions
from zenml.zen_stores.retention.bundle import Bundle
from zenml.zen_stores.retention.capture import CapturedTree, capture_tree
from zenml.zen_stores.retention.catalog import Cursor, RetentionState
from zenml.zen_stores.retention.eligibility import (
    ArchivableTree,
    canonical_root_predicate,
    inspect_tree,
    tree_limits,
)
from zenml.zen_stores.retention.manifest import (
    TABLE_ORDER,
    ConfigurationRecord,
    Manifest,
    SnapshotRecord,
    StepRecord,
    canonical_json,
    sha256_hex,
)
from zenml.zen_stores.retention.schema_mapping import (
    ARCHIVABLE_RECORD_SCHEMAS,
    schema_for_record,
)
from zenml.zen_stores.schemas import (
    ArchiveBundleSchema,
    ModelVersionPipelineRunSchema,
    PipelineRunSchema,
    ProjectSchema,
    StepConfigurationSchema,
)

logger = get_logger(__name__)


def discover_archive_roots(
    session: Session,
    project_id: UUID,
    policy: RetentionSettings,
    now: datetime,
    after: Optional[Cursor],
    limit: int,
) -> List[Cursor]:
    """Return a keyset page of roots for the bounded archive pass.

    Child and expensive exclusions remain part of per-tree eligibility.

    Args:
        session: Short read transaction.
        project_id: Authorized project.
        policy: Fixed cycle policy.
        now: Fixed cycle evaluation time.
        after: Last examined root, including failed or excluded trees.
        limit: Maximum identities to fetch, including any lookahead.

    Returns:
        Ordered non-null end times and canonical root IDs.
    """
    if policy.archive_after_days is None:
        return []
    statement = select(
        col(PipelineRunSchema.end_time), col(PipelineRunSchema.id)
    ).where(
        col(PipelineRunSchema.project_id) == project_id,
        canonical_root_predicate(),
        col(PipelineRunSchema.archive_bundle_id).is_(None),
        col(PipelineRunSchema.retain).is_(False),
        col(PipelineRunSchema.end_time)
        < now - timedelta(days=policy.archive_after_days),
    )
    if not policy.archive_model_linked_runs:
        statement = statement.where(
            ~select(col(ModelVersionPipelineRunSchema.id))
            .where(
                col(ModelVersionPipelineRunSchema.pipeline_run_id)
                == col(PipelineRunSchema.id)
            )
            .exists()
        )
    if after:
        statement = statement.where(
            or_(
                col(PipelineRunSchema.end_time) > after.end_time,
                (col(PipelineRunSchema.end_time) == after.end_time)
                & (col(PipelineRunSchema.id) > after.run_id),
            )
        )
    return [
        Cursor(end_time=end_time, run_id=run_id)
        for end_time, run_id in session.execute(
            statement.order_by(
                col(PipelineRunSchema.end_time), col(PipelineRunSchema.id)
            ).limit(limit)
        )
        if end_time is not None
    ]


class PreparedArchive(BaseModel):
    """Read-back-verified bytes and the SQL authority that must still match."""

    model_config = ConfigDict(frozen=True)

    claim: claims.ArchiveClaim
    manifest: Manifest
    fingerprint: str
    evaluated_at: datetime
    uri: str
    policy_raw: Optional[str]
    schema_revision: str


class ArchivePass:
    """Own one scan's budgets, checkpoints, and fenced tree retirement."""

    MAX_SECONDS: ClassVar[int] = 60
    ACTIVE_OUTCOMES: ClassVar[frozenset[RetentionOutcome]] = frozenset(
        {RetentionOutcome.ACCEPTED, RetentionOutcome.RUNNING}
    )

    def __init__(
        self,
        engine: Engine,
        storage: BaseArtifactStore,
        project_id: UUID,
        policy: RetentionSettings,
    ) -> None:
        """Bind an enabled policy and initialize one pass without database writes.

        Args:
            engine: Metadata database.
            storage: Registered artifact store, already resolved by the caller.
            project_id: Authorized project.
            policy: Saved project policy for this invocation.

        Raises:
            IllegalOperationError: The project has no archive age configured.
        """
        if policy.archive_after_days is None:
            raise IllegalOperationError(
                "Execution retention is disabled for this project."
            )
        self.engine, self.storage = engine, storage
        self.project_id, self.policy = project_id, policy.model_copy(deep=True)
        self.operation_id = uuid4()
        self.owner = claims.Claim.owner_identity(self.operation_id)
        self.claim: Optional[claims.ArchiveClaim] = None
        self.remaining_rows = policy.max_rows
        self.remaining_bytes = policy.max_bytes
        self.cursor: Optional[Cursor] = None
        self.state = RetentionState()
        self.state_raw: Optional[str] = None
        self.policy_raw: Optional[str] = None

    def accept(self) -> None:
        """Persist acceptance, propagating conflicts if the saved policy changed."""
        self._write_outcome(RetentionOutcome.ACCEPTED)

    def abort(self, error_code: RetentionFailure) -> None:
        """Record a failed submission without exposing persistence internals.

        Args:
            error_code: Safe lifecycle failure classification.
        """
        self._write_outcome(RetentionOutcome.FAILED, error_code)

    def run(self) -> RetentionState:
        """Archive a bounded scan, checkpointing rejected roots as well as successes.

        Returns:
            Persisted succeeded, paused, or failed pass state.
        """
        if self.state.operation_id != self.operation_id:
            self.accept()
        if self.state.operation_id != self.operation_id:
            return self.state
        started = monotonic()
        try:
            if not self._probe_storage():
                return self._write_outcome(
                    RetentionOutcome.FAILED,
                    RetentionFailure.STORAGE_CONFIGURATION,
                )
            with Session(self.engine) as session:
                self.evaluated_at = transactions.database_now(session)
                roots = discover_archive_roots(
                    session,
                    self.project_id,
                    self.policy,
                    self.evaluated_at,
                    self.cursor,
                    self.policy.max_trees + 1,
                )
            for cursor in roots[: self.policy.max_trees]:
                if (
                    monotonic() - started >= self.MAX_SECONDS
                    or self.remaining_rows <= 0
                    or self.remaining_bytes <= 0
                ):
                    return self._write_outcome(RetentionOutcome.PAUSED)
                paused = self._process_root(cursor)
                if paused is not None:
                    return paused
            outcome = (
                RetentionOutcome.SUCCEEDED
                if len(roots) <= self.policy.max_trees
                else RetentionOutcome.PAUSED
            )
            return self._write_outcome(outcome)
        except Exception as error:
            logger.error(
                "Retention pass for project %s failed (%s)",
                self.project_id,
                type(error).__name__,
            )
            return self._write_outcome(
                RetentionOutcome.FAILED, RetentionFailure.ARCHIVE_FAILED
            )

    def _probe_storage(self) -> bool:
        """Check writable, readable storage and remove the temporary probe.

        Returns:
            Whether the read-back bytes match the unique probe.
        """
        probe = f"{self._storage_prefix()}/_retention-probes/{uuid4()}"
        nonce = uuid4().hex.encode()
        self.storage.makedirs(probe.rsplit("/", 1)[0])
        try:
            with self.storage.open(probe, "wb") as target:
                target.write(nonce)
            with self.storage.open(probe, "rb") as source:
                return bool(source.read(len(nonce) + 1) == nonce)
        finally:
            if self.storage.exists(probe):
                self.storage.remove(probe)

    def _storage_prefix(self) -> str:
        """Return the configured storage directory for this server's archives.

        Returns:
            Artifact store path with the configured archive prefix.

        Raises:
            IllegalOperationError: If the prefix contains a traversal segment.
        """
        prefix = (
            ServerConfiguration.get_server_config().archive_path_prefix.strip(
                "/"
            )
        )
        parts = [part for part in prefix.split("/") if part]
        if any(part in {".", ".."} for part in parts):
            raise IllegalOperationError(
                "Archive path prefix must not contain '.' or '..' segments."
            )
        prefix = "/".join(parts)
        return f"{self.storage.path.rstrip('/')}/{prefix}".rstrip("/")

    def _process_root(self, cursor: Cursor) -> Optional[RetentionState]:
        """Archive or checkpoint one root without exceeding this pass's budget.

        Args:
            cursor: Discovered root in scan order.

        Returns:
            Paused state when a whole tree cannot fit, otherwise None.
        """
        with Session(self.engine) as session:
            tree = inspect_tree(
                session,
                self.project_id,
                cursor.run_id,
                self.policy,
                tree_limits(self.policy),
                self.evaluated_at,
                max_run_ids=self.remaining_rows,
            )
        if tree.exclusion == RetentionFailure.PASS_BUDGET:
            return self._write_outcome(RetentionOutcome.PAUSED)
        self.cursor = cursor
        if tree.exclusion is None:
            try:
                self._retire(self._archive_tree(cursor, tree))
                return None
            except ExecutionRetentionConflictError as error:
                if error.error_code == RetentionFailure.PASS_BUDGET:
                    return self._write_outcome(RetentionOutcome.PAUSED)
                # Stale or busy trees are reconsidered in the next scan.
            finally:
                self._fail_claim(RetentionFailure.ARCHIVE_FAILED)
        self.remaining_rows -= max(1, len(tree.tree_run_ids))
        with transactions.transaction(self.engine) as session:
            self._write_cursor(session, cursor)
        return None

    def _fail_claim(self, reason: RetentionFailure) -> None:
        """Release this pass's pending archive unless its owner changed.

        Args:
            reason: Safe failure classification for the retained archive.
        """
        if self.claim is not None:
            try:
                with transactions.transaction(self.engine) as session:
                    self.claim.fail(session, reason)
            except ExecutionRetentionConflictError:
                # A replacement owner already controls this archive.
                pass
            self.claim = None

    def _archive_tree(
        self, cursor: Cursor, tree: ArchivableTree
    ) -> PreparedArchive:
        """Claim, capture, upload, and read back one previously inspected tree.

        Args:
            cursor: Root to checkpoint only after verified retirement.
            tree: Existing inventory whose eligibility is rechecked under final locks.

        Returns:
            Immutable descriptor for atomic retirement.

        Raises:
            ExecutionRetentionConflictError: The captured tree exceeds the remaining budget.
        """
        self.cursor = cursor
        if (
            tree.row_count > self.remaining_rows
            or tree.estimated_bytes > self.remaining_bytes
        ):
            raise ExecutionRetentionConflictError(
                "Tree exceeds the remaining pass budget.",
                error_code=RetentionFailure.PASS_BUDGET,
            )
        bundle_id = uuid4()
        prefix = f"{self._storage_prefix()}/archive"
        uri = f"{prefix}/{self.project_id}/{tree.root_run_id}/{bundle_id}"
        with transactions.transaction(self.engine) as session:
            claim = claims.ArchiveClaim.take(
                session,
                project_id=self.project_id,
                root_id=tree.root_run_id,
                bundle_id=bundle_id,
                owner=self.owner,
                uri=uri,
            )
            self.claim = claim
            revision = transactions.writer_revision(session)
            evaluated_at = transactions.database_now(session)
        with Session(self.engine) as session:
            captured = capture_tree(session, tree)
            self._require_capture_budget(captured)
        with TemporaryDirectory(prefix="zenml-retention-") as scratch:
            bundle = Bundle.create(
                captured.records,
                Path(scratch),
                bundle_id=bundle_id,
                project_id=self.project_id,
                root_run_id=tree.root_run_id,
                created_at=evaluated_at,
            )
            with transactions.transaction(self.engine) as session:
                claim.renew(session)
            self._upload(bundle, uri)
            with transactions.transaction(self.engine) as session:
                claim.renew(session)
            self._verify_upload(bundle, uri, Path(scratch))
            with transactions.transaction(self.engine) as session:
                claim.renew(session)
        return PreparedArchive(
            claim=claim,
            manifest=bundle.manifest,
            fingerprint=captured.fingerprint,
            evaluated_at=evaluated_at,
            uri=uri,
            policy_raw=self.policy_raw,
            schema_revision=revision,
        )

    def _upload(self, bundle: Bundle, uri: str) -> None:
        """Upload the immutable object before publishing its manifest.

        Args:
            bundle: Locally verified archive and manifest.
            uri: Reserved archive directory.
        """
        self.storage.makedirs(uri)
        with (
            bundle.path.open("rb") as source,
            self.storage.open(f"{uri}/{bundle.path.name}", "wb") as target,
        ):
            copyfileobj(source, target)
        with self.storage.open(f"{uri}/manifest.json", "wb") as target:
            target.write(
                canonical_json(bundle.manifest.model_dump(mode="json"))
            )

    def _verify_upload(self, bundle: Bundle, uri: str, scratch: Path) -> None:
        """Read uploaded bytes directly and verify the complete archive again.

        Args:
            bundle: Expected local object descriptor.
            uri: Uploaded immutable archive directory.
            scratch: Current operation's private scratch directory.

        Raises:
            ExecutionRetentionIntegrityError: Uploaded manifest bytes differ.
        """
        manifest_bytes = canonical_json(
            bundle.manifest.model_dump(mode="json")
        )
        with self.storage.open(f"{uri}/manifest.json", "rb") as source:
            if source.read(len(manifest_bytes) + 1) != manifest_bytes:
                raise ExecutionRetentionIntegrityError(
                    "Uploaded manifest differs from the verified capture."
                )
        readback = scratch / "readback.tar.gz"
        with self.storage.open(f"{uri}/{bundle.path.name}", "rb") as source:
            readback.write_bytes(source.read(bundle.manifest.object_bytes + 1))
        Bundle(manifest=bundle.manifest, path=readback).records(scratch)

    def _retire(self, prepared: PreparedArchive) -> None:
        """Commit detail removal, archive authority, and progress together.

        Args:
            prepared: Uploaded descriptor and captured authority.

        Raises:
            Exception: Any failed recheck or write rolls back the full tree.
        """
        previous_rows, previous_bytes = (
            self.remaining_rows,
            self.remaining_bytes,
        )
        try:
            with transactions.transaction(self.engine) as session:
                captured = self._recapture(session, prepared)
                self._retire_rows(session, prepared, captured)
                self.state.last_outcome = RetentionOutcome.RUNNING
                prepared.claim.complete(
                    session,
                    uri=prepared.uri,
                    size_bytes=prepared.manifest.object_bytes,
                    manifest_hash=sha256_hex(
                        canonical_json(
                            prepared.manifest.model_dump(mode="json")
                        )
                    ),
                )
                self._write_cursor(session, self.cursor)
        except Exception:
            self.remaining_rows, self.remaining_bytes = (
                previous_rows,
                previous_bytes,
            )
            raise
        self.claim = None

    def _recapture(
        self, session: Session, prepared: PreparedArchive
    ) -> CapturedTree:
        """Lock the tree and require the captured policy, schema, and content.

        Args:
            session: Final mutation transaction.
            prepared: Original verified descriptor.

        Returns:
            A semantically identical capture under the shared lock order.

        Raises:
            ExecutionRetentionConflictError: Policy, revision, or content changed.
        """
        from zenml.zen_stores.retention.catalog import lock_tree

        lock_tree(
            session,
            prepared.claim,
            {
                section.table: section.ids
                for section in prepared.manifest.sections
            },
        )
        self._require_unchanged(session, prepared)
        tree = inspect_tree(
            session,
            self.project_id,
            prepared.claim.root_run_id,
            self.policy,
            tree_limits(self.policy),
            prepared.evaluated_at,
        )
        required_rows = tree.row_count
        required_bytes = tree.estimated_bytes
        if (
            required_rows > self.remaining_rows
            or required_bytes > self.remaining_bytes
        ):
            raise ExecutionRetentionConflictError(
                "Locked tree exceeds the remaining pass budget.",
                error_code=RetentionFailure.PASS_BUDGET,
            )
        captured = capture_tree(session, tree)
        self._require_capture_budget(captured)
        if captured.fingerprint != prepared.fingerprint:
            raise ExecutionRetentionConflictError(
                "Execution content or membership changed after capture."
            )
        self.remaining_rows -= len(captured.records)
        self.remaining_bytes -= required_bytes
        return captured

    def _require_capture_budget(self, captured: CapturedTree) -> None:
        """Keep the actual record count within this pass's remaining allowance.

        Args:
            captured: Detached records from either capture phase.

        Raises:
            ExecutionRetentionConflictError: The complete capture exceeds the row budget.
        """
        if len(captured.records) > self.remaining_rows:
            raise ExecutionRetentionConflictError(
                "Captured tree exceeds the remaining row budget.",
                error_code=RetentionFailure.PASS_BUDGET,
            )

    def _require_unchanged(
        self, session: Session, prepared: PreparedArchive
    ) -> None:
        """Require the policy and writer revision used to capture this tree.

        Args:
            session: Final mutation transaction holding the tree locks.
            prepared: Captured policy and revision authority.

        Raises:
            ExecutionRetentionConflictError: Policy or writer revision changed.
        """
        raw = session.execute(
            select(col(ProjectSchema.retention_settings)).where(
                col(ProjectSchema.id) == self.project_id
            )
        ).scalar_one()
        if raw != prepared.policy_raw:
            raise ExecutionRetentionConflictError(
                "Retention policy changed after capture."
            )
        if transactions.writer_revision(session) != prepared.schema_revision:
            raise ExecutionRetentionConflictError(
                "Database schema changed after capture."
            )

    def _retire_rows(
        self,
        session: Session,
        prepared: PreparedArchive,
        capture: CapturedTree,
    ) -> None:
        """Clear allowlisted payloads and delete owned configuration records.

        Args:
            session: Transaction holding the revalidated tree locks.
            prepared: Archive acquiring SQL authority.
            capture: Exact records re-read under those locks.

        Raises:
            ExecutionRetentionConflictError: Captured configuration deletion differs.
        """
        marker = {"archive_bundle_id": prepared.claim.bundle_id}
        ordered_records = sorted(
            capture.records, key=lambda record: TABLE_ORDER.index(record.table)
        )
        for record in ordered_records:
            if record.table == ConfigurationRecord.table:
                continue
            values: Dict[str, Any] = {
                column: None for column in record.archived_columns
            }
            if type(record) in ARCHIVABLE_RECORD_SCHEMAS:
                values.update(marker)
            if record.table == SnapshotRecord.table:
                values.update(
                    pipeline_configuration=canonical_json({}).decode(),
                    client_environment=canonical_json({}).decode(),
                )
            if isinstance(record, StepRecord):
                values.update(
                    step_type=record.step_type,
                    substitutions=canonical_json(record.substitutions).decode()
                    if record.substitutions is not None
                    else None,
                )
            transactions.update_identity(
                session, schema_for_record(record), record.id, values
            )
        ids = [
            record.id
            for record in capture.records
            if record.table == ConfigurationRecord.table
        ]
        deleted = sum(
            session.connection()
            .execute(
                delete(StepConfigurationSchema).where(
                    col(StepConfigurationSchema.id).in_(group)
                )
            )
            .rowcount
            for group in transactions.batches(ids)
        )
        if deleted != len(ids):
            raise ExecutionRetentionConflictError(
                "Captured detail deletion count changed."
            )

    def _read_cursor(self, session: Session) -> Optional[Cursor]:
        """Read the current project checkpoint and exact serialized policy.

        Args:
            session: Caller-owned SQL transaction.

        Returns:
            Last committed root in the current scan.
        """
        project = session.execute(
            select(ProjectSchema).where(
                col(ProjectSchema.id) == self.project_id
            )
        ).scalar_one()
        self.state_raw = project.retention_state
        self.policy_raw = project.retention_settings
        self.state = (
            RetentionState.model_validate_json(self.state_raw)
            if self.state_raw
            else RetentionState()
        )
        return self.state.cursor

    def _write_cursor(
        self, session: Session, cursor: Optional[Cursor]
    ) -> None:
        """Compare and replace the full policy-bound project checkpoint.

        Args:
            session: Mutation transaction, shared with retirement on success.
            cursor: Root checkpoint, or None after exhausting the scan.

        Raises:
            ExecutionRetentionConflictError: Another writer changed state or policy.
        """
        predicates = [col(ProjectSchema.id) == self.project_id]
        for column, expected in (
            (col(ProjectSchema.retention_state), self.state_raw),
            (col(ProjectSchema.retention_settings), self.policy_raw),
        ):
            predicates.append(
                column.is_(None)
                if expected is None
                else cast(column, LargeBinary) == expected.encode()
            )
        self.state.cursor = cursor
        self.state.operation_expires_at = (
            transactions.database_now(session) + claims.Claim.LEASE
            if self.state.last_outcome in self.ACTIVE_OUTCOMES
            else None
        )
        serialized = self.state.model_dump_json()
        statement = (
            update(ProjectSchema)
            .where(*predicates)
            .values(retention_state=serialized)
        )
        if session.connection().execute(statement).rowcount != 1:
            raise ExecutionRetentionConflictError(
                "Retention state or policy changed during the pass."
            )
        self.state_raw = serialized

    def _write_outcome(
        self,
        outcome: RetentionOutcome,
        failure: Optional[RetentionFailure] = None,
    ) -> RetentionState:
        """Persist advisory progress while preserving another pass's checkpoint.

        Args:
            outcome: Latest pass outcome.
            failure: Fixed classification for server logs, never exception text.

        Returns:
            The committed project state.

        Raises:
            ExecutionRetentionConflictError: The saved policy changed before acceptance.
        """
        with transactions.transaction(self.engine) as session:
            self.cursor = self._read_cursor(session)
            current_time = transactions.database_now(session)
            if outcome == RetentionOutcome.ACCEPTED:
                saved_policy = (
                    RetentionSettings.model_validate_json(self.policy_raw)
                    if self.policy_raw
                    else RetentionSettings()
                )
                if saved_policy != self.policy:
                    raise ExecutionRetentionConflictError(
                        "Retention policy changed before pass acceptance."
                    )
                if (
                    self.state.operation_id is not None
                    and self.state.operation_id != self.operation_id
                    and self.state.last_outcome in self.ACTIVE_OUTCOMES
                    and self.state.operation_expires_at is not None
                    and self.state.operation_expires_at > current_time
                    and not self._operation_claim_expired(session)
                ):
                    return self.state
                self.state.operation_id = self.operation_id
            elif self.state.operation_id != self.operation_id:
                return self.state
            self.state.last_outcome = outcome
            self.state.last_finished_at = (
                None if outcome in self.ACTIVE_OUTCOMES else current_time
            )
            if outcome == RetentionOutcome.SUCCEEDED:
                self.cursor = None
            self._write_cursor(session, self.cursor)
        if failure is not None:
            logger.warning(
                "Retention pass failed for project %s (%s)",
                self.project_id,
                failure,
            )
        return self.state

    def _operation_claim_expired(self, session: Session) -> bool:
        """Check whether the recorded operation's own tree claim has expired.

        A live project lease normally protects the running pass. Its tree
        claim can expire earlier when the worker stalls mid-tree, so that
        expiry allows an early takeover. Claims of other operations, such as
        one abandoned on a root that is now excluded, must not count.

        Args:
            session: Transaction holding the project state update decision.

        Returns:
            Whether a pending claim owned by the recorded operation expired.
        """
        owner_suffix = f":{self.state.operation_id}"
        return (
            session.execute(
                select(col(ArchiveBundleSchema.id))
                .where(
                    col(ArchiveBundleSchema.project_id) == self.project_id,
                    col(ArchiveBundleSchema.status)
                    == ArchiveBundleStatus.PENDING,
                    col(ArchiveBundleSchema.active_root_id).is_not(None),
                    col(ArchiveBundleSchema.claimed_by).endswith(
                        owner_suffix, autoescape=True
                    ),
                    col(ArchiveBundleSchema.claim_expires_at)
                    <= transactions.database_now(session),
                )
                .limit(1)
            ).scalar_one_or_none()
            is not None
        )
