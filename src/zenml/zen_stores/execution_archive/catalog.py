#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
#  implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Catalog state transitions and fenced ownership for execution archives."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, FrozenSet, List, Optional
from uuid import UUID

from sqlalchemy import update
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, desc, or_, select

from zenml.constants import MAX_ZENML_SERVER_EXECUTION_ARCHIVE_ERROR_LENGTH
from zenml.enums import ExecutionArchiveState
from zenml.exceptions import ExecutionArchiveStateError
from zenml.logger import get_logger
from zenml.models import ExecutionArchiveObject, ExecutionArchiveResponse
from zenml.utils.time_utils import utc_now
from zenml.zen_stores.schemas import (
    ExecutionArchiveSchema,
    ProjectSchema,
    ServerSettingsSchema,
)

S = ExecutionArchiveState
logger = get_logger(__name__)
_TRANSITIONS: Dict[S, FrozenSet[S]] = {
    S.EXPORTING: frozenset({S.EXPORTING, S.VERIFIED, S.FAILED, S.CORRUPT}),
    S.VERIFIED: frozenset({S.VERIFIED, S.COMPACTING, S.FAILED, S.CORRUPT}),
    S.FAILED: frozenset({S.EXPORTING}),
    S.COMPACTING: frozenset({S.COMPACTING, S.COLD, S.RESTORING, S.CORRUPT}),
    S.COLD: frozenset({S.COLD, S.RESTORING, S.CORRUPT}),
    S.RESTORING: frozenset({S.RESTORING, S.RESTORED, S.COLD, S.CORRUPT}),
    S.RESTORED: frozenset(),
    S.CORRUPT: frozenset(),
}
_RESUMABLE_EXPORT_STATES = frozenset({S.EXPORTING, S.FAILED})
_PURGEABLE_SUPERSEDED_STATES = frozenset(
    {S.EXPORTING, S.VERIFIED, S.FAILED, S.RESTORED}
)
_SUPERSEDING_STATES = frozenset(
    {S.VERIFIED, S.COMPACTING, S.COLD, S.RESTORING, S.RESTORED}
)


@dataclass(frozen=True)
class ExecutionArchiveClaim:
    """Fencing identity for one leased archive operation."""

    archive: ExecutionArchiveResponse
    owner: str
    token: int

    @property
    def archive_id(self) -> UUID:
        """Return the claimed generation ID.

        Returns:
            Archive generation ID.
        """
        return self.archive.id


class ExecutionArchiveCatalog:
    """Own all catalog transitions and reject stale workers."""

    def __init__(self, engine: Engine) -> None:
        """Initialize the catalog.

        Args:
            engine: SQL store engine.
        """
        self._engine = engine

    def start_export(
        self,
        *,
        project_id: UUID,
        root_run_id: UUID,
        source_fingerprint: str,
        source_updated_at: datetime,
        storage_target_digest: str,
        source_bytes: int,
        owner: str,
        lease_seconds: float,
    ) -> ExecutionArchiveClaim:
        """Create, resume, or verify a generation and claim it atomically.

        Args:
            project_id: Project owning the root run.
            root_run_id: Root execution run.
            source_fingerprint: Semantic fingerprint captured from SQL.
            source_updated_at: Latest mutation included in the fingerprint.
            storage_target_digest: Immutable target identity.
            source_bytes: Payload bytes currently held in SQL.
            owner: Unique worker identity.
            lease_seconds: Initial ownership lease duration.

        Returns:
            Claimed generation with a new fencing token.
        """

        def attempt() -> ExecutionArchiveClaim:
            return self._start_export(
                project_id=project_id,
                root_run_id=root_run_id,
                source_fingerprint=source_fingerprint,
                source_updated_at=source_updated_at,
                storage_target_digest=storage_target_digest,
                source_bytes=source_bytes,
                owner=owner,
                lease_seconds=lease_seconds,
            )

        try:
            return attempt()
        except IntegrityError:
            # Two workers may both observe an empty catalog. The unique
            # root/generation constraint picks the winner; retry and claim
            # that row instead of creating another generation.
            return attempt()

    def _start_export(
        self,
        *,
        project_id: UUID,
        root_run_id: UUID,
        source_fingerprint: str,
        source_updated_at: datetime,
        storage_target_digest: str,
        source_bytes: int,
        owner: str,
        lease_seconds: float,
    ) -> ExecutionArchiveClaim:
        with Session(self._engine) as session:
            self._require_project(session, project_id)
            self._require_target(session, storage_target_digest)
            latest = session.exec(
                select(ExecutionArchiveSchema)
                .where(col(ExecutionArchiveSchema.root_run_id) == root_run_id)
                .order_by(desc(col(ExecutionArchiveSchema.generation)))
                .with_for_update()
            ).first()
            schema = self._generation_for_export(
                latest=latest,
                project_id=project_id,
                root_run_id=root_run_id,
                source_fingerprint=source_fingerprint,
                source_updated_at=source_updated_at,
                storage_target_digest=storage_target_digest,
                source_bytes=source_bytes,
            )
            if schema is not latest:
                session.add(schema)
                session.flush()
            elif schema.archive_state in _RESUMABLE_EXPORT_STATES:
                schema.state = S.EXPORTING.value
                schema.last_error = None
            token = self._acquire(
                schema,
                owner=owner,
                lease_seconds=lease_seconds,
            )
            schema.updated = utc_now()
            session.add(schema)
            session.flush()
            claim = ExecutionArchiveClaim(
                archive=schema.to_model(), owner=owner, token=token
            )
            session.commit()
            return claim

    @staticmethod
    def _generation_for_export(
        *,
        latest: Optional[ExecutionArchiveSchema],
        project_id: UUID,
        root_run_id: UUID,
        source_fingerprint: str,
        source_updated_at: datetime,
        storage_target_digest: str,
        source_bytes: int,
    ) -> ExecutionArchiveSchema:
        if latest is not None and latest.project_id != project_id:
            raise ExecutionArchiveStateError(
                "The root run belongs to a different project."
            )
        if latest is not None and latest.requires_restore:
            raise ExecutionArchiveStateError(
                f"Execution archive {latest.id} is {latest.state}; restore "
                "it before exporting this execution tree again."
            )
        if (
            latest is not None
            and latest.source_fingerprint == source_fingerprint
            and latest.storage_target_digest == storage_target_digest
            and latest.archive_state in _RESUMABLE_EXPORT_STATES | {S.VERIFIED}
        ):
            latest.source_bytes = source_bytes
            latest.source_updated_at = source_updated_at
            return latest
        return ExecutionArchiveSchema(
            project_id=project_id,
            root_run_id=root_run_id,
            generation=latest.generation + 1 if latest else 1,
            state=S.EXPORTING.value,
            source_fingerprint=source_fingerprint,
            source_updated_at=source_updated_at,
            storage_target_digest=storage_target_digest,
            source_bytes=source_bytes,
        )

    @staticmethod
    def _acquire(
        schema: ExecutionArchiveSchema, *, owner: str, lease_seconds: float
    ) -> int:
        now = utc_now()
        if (
            schema.owner not in (None, owner)
            and schema.owner_expires_at is not None
            and schema.owner_expires_at > now
        ):
            raise ExecutionArchiveStateError(
                f"Execution archive {schema.id} is being processed by "
                f"{schema.owner}."
            )
        schema.claim_token += 1
        schema.owner = owner
        schema.owner_expires_at = now + timedelta(seconds=lease_seconds)
        return schema.claim_token

    def renew(
        self, claim: ExecutionArchiveClaim, *, lease_seconds: float
    ) -> ExecutionArchiveClaim:
        """Renew a lease if no newer worker fenced it.

        Args:
            claim: Existing ownership claim.
            lease_seconds: Renewed duration.

        Returns:
            Claim with refreshed archive state.
        """
        with Session(self._engine) as session:
            schema = self._lock(session, claim.archive_id)
            self._require_token(schema, claim, require_live=False)
            schema.owner_expires_at = utc_now() + timedelta(
                seconds=lease_seconds
            )
            schema.updated = utc_now()
            session.add(schema)
            session.flush()
            renewed = ExecutionArchiveClaim(
                archive=schema.to_model(),
                owner=claim.owner,
                token=claim.token,
            )
            session.commit()
            return renewed

    def mark_verified(
        self,
        claim: ExecutionArchiveClaim,
        *,
        key: str,
        object_: ExecutionArchiveObject,
    ) -> ExecutionArchiveResponse:
        """Commit object metadata and the verified state together.

        Args:
            claim: Current fenced ownership.
            key: Full immutable object key.
            object_: Verified object metadata.

        Returns:
            Verified archive generation.
        """
        with Session(self._engine) as session:
            schema = self.transition(session, claim, S.VERIFIED)
            schema.set_object(key=key, object_=object_)
            schema.last_error = None
            session.add(schema)
            session.flush()
            self._queue_superseded(session, schema)
            response = schema.to_model()
            session.commit()
            return response

    def record_error(
        self, claim: ExecutionArchiveClaim, error: str
    ) -> ExecutionArchiveResponse:
        """Record an operational error without changing authority state.

        Args:
            claim: Current fenced ownership.
            error: Operator-facing failure message.

        Returns:
            Updated archive generation.
        """
        with Session(self._engine) as session:
            schema = self._claimed(session, claim)
            schema.last_error = error[
                :MAX_ZENML_SERVER_EXECUTION_ARCHIVE_ERROR_LENGTH
            ]
            schema.updated = utc_now()
            session.add(schema)
            session.flush()
            response = schema.to_model()
            session.commit()
            return response

    def clear_error(
        self, claim: ExecutionArchiveClaim
    ) -> ExecutionArchiveResponse:
        """Clear a previous operational error after successful verification.

        Args:
            claim: Current fenced ownership.

        Returns:
            Updated archive generation.
        """
        with Session(self._engine) as session:
            schema = self._claimed(session, claim)
            schema.last_error = None
            schema.updated = utc_now()
            session.add(schema)
            session.flush()
            response = schema.to_model()
            session.commit()
            return response

    def mark_failed(
        self,
        claim: ExecutionArchiveClaim,
        *,
        corrupt: bool,
        error: str,
    ) -> ExecutionArchiveResponse:
        """Record a failed or corrupt export.

        Args:
            claim: Current fenced ownership.
            corrupt: Whether trusted object bytes violated their contract.
            error: Operator-facing failure message.

        Returns:
            Failed archive generation.
        """
        state = S.CORRUPT if corrupt else S.FAILED
        with Session(self._engine) as session:
            schema = self.transition(session, claim, state)
            schema.last_error = error[
                :MAX_ZENML_SERVER_EXECUTION_ARCHIVE_ERROR_LENGTH
            ]
            session.add(schema)
            session.flush()
            response = schema.to_model()
            session.commit()
            return response

    def try_record_failure(
        self,
        claim: ExecutionArchiveClaim,
        error: Exception,
        *,
        state: Optional[S] = None,
    ) -> bool:
        """Record a failure unless another worker fenced this claim.

        Args:
            claim: Worker ownership that observed the failure.
            error: Failure to expose to operators.
            state: Optional terminal export state. Omit to preserve the
                current lifecycle state.

        Returns:
            Whether this worker still owned the generation and recorded the
            failure.

        Raises:
            ValueError: If `state` is neither `FAILED` nor `CORRUPT`.
        """
        if state not in {None, S.FAILED, S.CORRUPT}:
            raise ValueError(
                "An archive failure can only preserve state or become "
                "failed or corrupt."
            )
        with Session(self._engine) as session:
            try:
                schema = self._claimed(session, claim)
            except ExecutionArchiveStateError:
                logger.warning(
                    "The claim for execution archive %s is no longer current; "
                    "preserving its state after a failed operation.",
                    claim.archive_id,
                )
                return False
            if state is not None and schema.archive_state != state:
                schema = self.transition(session, claim, state)
            schema.last_error = str(error)[
                :MAX_ZENML_SERVER_EXECUTION_ARCHIVE_ERROR_LENGTH
            ]
            schema.updated = utc_now()
            session.add(schema)
            session.commit()
        return True

    def release(self, claim: ExecutionArchiveClaim) -> None:
        """Release a claim if it still belongs to this worker.

        Args:
            claim: Ownership to release.
        """
        with Session(self._engine) as session:
            schema = session.exec(
                select(ExecutionArchiveSchema)
                .where(col(ExecutionArchiveSchema.id) == claim.archive_id)
                .with_for_update()
            ).one_or_none()
            if schema is None:
                return
            if (
                schema.owner == claim.owner
                and schema.claim_token == claim.token
            ):
                schema.owner = None
                schema.owner_expires_at = None
                schema.updated = utc_now()
                session.add(schema)
                session.commit()

    @staticmethod
    def transition(
        session: Session,
        claim: ExecutionArchiveClaim,
        to: S,
        *,
        committed_at: Optional[datetime] = None,
        compacted_at: Optional[datetime] = None,
        restored_at: Optional[datetime] = None,
    ) -> ExecutionArchiveSchema:
        """Apply one fenced lifecycle transition in an existing transaction.

        Args:
            session: SQL transaction.
            claim: Current fenced ownership.
            to: Destination state.
            committed_at: Authority-switch timestamp, if applicable.
            compacted_at: Compaction completion timestamp, if applicable.
            restored_at: Restore completion timestamp, if applicable.

        Returns:
            Locked and updated catalog row.

        Raises:
            ExecutionArchiveStateError: If ownership or the transition is
                invalid.
        """
        schema = ExecutionArchiveCatalog._claimed(session, claim)
        if to not in _TRANSITIONS[schema.archive_state]:
            raise ExecutionArchiveStateError(
                f"Execution archive {schema.id} is {schema.state} and cannot "
                f"become {to.value}."
            )
        if to.is_authoritative and not schema.archive_state.is_authoritative:
            other = session.exec(
                select(ExecutionArchiveSchema.id)
                .where(
                    col(ExecutionArchiveSchema.root_run_id)
                    == schema.root_run_id
                )
                .where(col(ExecutionArchiveSchema.id) != schema.id)
                .where(
                    or_(
                        col(ExecutionArchiveSchema.state).in_(
                            [
                                state.value
                                for state in S
                                if state.is_authoritative
                            ]
                        ),
                        (
                            (
                                col(ExecutionArchiveSchema.state)
                                == S.CORRUPT.value
                            )
                            & col(ExecutionArchiveSchema.compacted_at).is_not(
                                None
                            )
                            & col(ExecutionArchiveSchema.restored_at).is_(None)
                        ),
                    )
                )
                .with_for_update()
            ).first()
            if other is not None:
                raise ExecutionArchiveStateError(
                    f"Execution archive {other} is already authoritative "
                    "for this execution tree."
                )
        schema.state = to.value
        schema.committed_at = committed_at or schema.committed_at
        schema.compacted_at = compacted_at or schema.compacted_at
        schema.restored_at = restored_at or schema.restored_at
        schema.updated = utc_now()
        session.add(schema)
        return schema

    @staticmethod
    def _claimed(
        session: Session, claim: ExecutionArchiveClaim
    ) -> ExecutionArchiveSchema:
        schema = ExecutionArchiveCatalog._lock(session, claim.archive_id)
        ExecutionArchiveCatalog._require_token(
            schema, claim, require_live=True
        )
        return schema

    @staticmethod
    def _require_token(
        schema: ExecutionArchiveSchema,
        claim: ExecutionArchiveClaim,
        *,
        require_live: bool,
    ) -> None:
        if schema.owner != claim.owner or schema.claim_token != claim.token:
            raise ExecutionArchiveStateError(
                f"Execution archive {schema.id} is owned by a newer worker."
            )
        if require_live and (
            schema.owner_expires_at is None
            or schema.owner_expires_at <= utc_now()
        ):
            raise ExecutionArchiveStateError(
                f"The claim on execution archive {schema.id} expired."
            )

    @staticmethod
    def _lock(session: Session, archive_id: UUID) -> ExecutionArchiveSchema:
        schema = session.exec(
            select(ExecutionArchiveSchema)
            .where(col(ExecutionArchiveSchema.id) == archive_id)
            .with_for_update()
        ).one_or_none()
        if schema is None:
            raise ExecutionArchiveStateError(
                f"Execution archive {archive_id} does not exist."
            )
        return schema

    @staticmethod
    def _require_project(session: Session, project_id: UUID) -> None:
        project = session.exec(
            select(ProjectSchema.id)
            .where(col(ProjectSchema.id) == project_id)
            .with_for_update()
        ).one_or_none()
        if project is None:
            raise ExecutionArchiveStateError(
                f"Project {project_id} no longer exists."
            )

    @staticmethod
    def _require_target(session: Session, target_digest: str) -> None:
        current_digest = session.exec(
            select(ServerSettingsSchema.execution_archive_target_digest)
        ).one_or_none()
        if current_digest == target_digest:
            return

        settings = session.exec(
            select(ServerSettingsSchema).with_for_update()
        ).one_or_none()
        if settings is None:
            raise ExecutionArchiveStateError(
                "The server settings have not been initialized."
            )
        if settings.execution_archive_target_digest == target_digest:
            return
        existing = session.exec(
            select(ExecutionArchiveSchema.id).limit(1)
        ).first()
        if existing is not None:
            raise ExecutionArchiveStateError(
                "The execution archive target differs from an existing "
                "generation. Restore and purge existing archives before "
                "changing the target configuration."
            )
        settings.execution_archive_target_digest = target_digest
        settings.updated = utc_now()
        session.add(settings)

    @staticmethod
    def _queue_superseded(
        session: Session, schema: ExecutionArchiveSchema
    ) -> None:
        """Queue safe generations replaced by a verified generation.

        Args:
            session: Verification transaction.
            schema: Newly verified generation.
        """
        newer = session.exec(
            select(ExecutionArchiveSchema.id)
            .where(
                col(ExecutionArchiveSchema.root_run_id) == schema.root_run_id
            )
            .where(col(ExecutionArchiveSchema.generation) > schema.generation)
            .where(
                or_(
                    col(ExecutionArchiveSchema.state).in_(
                        [state.value for state in _SUPERSEDING_STATES]
                    ),
                    (col(ExecutionArchiveSchema.state) == S.CORRUPT.value)
                    & col(ExecutionArchiveSchema.compacted_at).is_not(None)
                    & col(ExecutionArchiveSchema.restored_at).is_(None),
                )
            )
            .limit(1)
        ).first()
        now = utc_now()
        if newer is not None and _is_superseded_purgeable(schema):
            schema.purge_pending_at = schema.purge_pending_at or now
            schema.updated = now
            session.add(schema)

        session.execute(
            update(ExecutionArchiveSchema)
            .where(
                col(ExecutionArchiveSchema.root_run_id) == schema.root_run_id
            )
            .where(col(ExecutionArchiveSchema.generation) < schema.generation)
            .where(col(ExecutionArchiveSchema.purge_pending_at).is_(None))
            .where(
                or_(
                    col(ExecutionArchiveSchema.state).in_(
                        [state.value for state in _PURGEABLE_SUPERSEDED_STATES]
                    ),
                    (col(ExecutionArchiveSchema.state) == S.CORRUPT.value)
                    & or_(
                        col(ExecutionArchiveSchema.compacted_at).is_(None),
                        col(ExecutionArchiveSchema.restored_at).is_not(None),
                    ),
                )
            )
            .values(purge_pending_at=now, updated=now)
        )

    def get(
        self, archive_id: UUID, *, project_id: Optional[UUID] = None
    ) -> Optional[ExecutionArchiveResponse]:
        """Load one archive generation.

        Args:
            archive_id: Generation ID.
            project_id: Required owning project, if supplied.

        Returns:
            Archive generation or `None`.
        """
        statement = select(ExecutionArchiveSchema).where(
            col(ExecutionArchiveSchema.id) == archive_id
        )
        if project_id is not None:
            statement = statement.where(
                col(ExecutionArchiveSchema.project_id) == project_id
            )
        with Session(self._engine) as session:
            schema = session.exec(statement).one_or_none()
            return schema.to_model() if schema else None

    def require(self, archive_id: UUID) -> ExecutionArchiveResponse:
        """Load a generation that must exist.

        Args:
            archive_id: Generation ID.

        Returns:
            Archive generation.

        Raises:
            ExecutionArchiveStateError: If it does not exist.
        """
        archive = self.get(archive_id)
        if archive is None:
            raise ExecutionArchiveStateError(
                f"Execution archive {archive_id} does not exist."
            )
        return archive

    def object_key(self, archive_id: UUID) -> str:
        """Load the object key of one generation.

        Args:
            archive_id: Generation ID.

        Returns:
            Full immutable object key.

        Raises:
            ExecutionArchiveStateError: If the generation or key is missing.
        """
        with Session(self._engine) as session:
            schema = session.get(ExecutionArchiveSchema, archive_id)
            if schema is None or schema.object_key is None:
                raise ExecutionArchiveStateError(
                    f"Execution archive {archive_id} has no object key."
                )
            return schema.object_key

    def list(
        self,
        *,
        project_id: UUID,
        state: Optional[S] = None,
        limit: int = 100,
    ) -> List[ExecutionArchiveResponse]:
        """List newest generations of one project.

        Args:
            project_id: Owning project.
            state: Optional state filter.
            limit: Maximum rows to return.

        Returns:
            Detached generations, newest first.

        Raises:
            ValueError: If the requested limit is not positive.
        """
        if limit <= 0:
            raise ValueError("Execution archive list limit must be positive.")
        statement = (
            select(ExecutionArchiveSchema)
            .where(col(ExecutionArchiveSchema.project_id) == project_id)
            .order_by(
                desc(col(ExecutionArchiveSchema.created)),
                desc(col(ExecutionArchiveSchema.generation)),
            )
            .limit(limit)
        )
        if state is not None:
            statement = statement.where(
                col(ExecutionArchiveSchema.state) == state.value
            )
        with Session(self._engine) as session:
            return [row.to_model() for row in session.exec(statement).all()]


def _is_superseded_purgeable(schema: ExecutionArchiveSchema) -> bool:
    """Return whether a replaced generation can be purged without restore.

    Args:
        schema: Replaced catalog generation.

    Returns:
        Whether purging the generation cannot remove authoritative payload.
    """
    return schema.archive_state in _PURGEABLE_SUPERSEDED_STATES or (
        schema.archive_state == S.CORRUPT and not schema.requires_restore
    )
