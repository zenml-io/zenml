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
"""Fenced, resumable compaction and restoration of execution archives."""

from datetime import datetime
from typing import TYPE_CHECKING, Callable, Optional, Sequence
from uuid import UUID

from sqlmodel import Session, col, select, update

from zenml.config.server_config import ServerConfiguration
from zenml.constants import (
    DEFAULT_ZENML_SERVER_EXECUTION_ARCHIVE_LEASE_SECONDS,
)
from zenml.enums import ExecutionArchiveState
from zenml.exceptions import (
    ArchiveUnavailableError,
    DoesNotExistException,
    ExecutionArchiveParityError,
    ExecutionArchiveStateError,
)
from zenml.logger import get_logger
from zenml.models import ExecutionArchiveResponse
from zenml.utils.time_utils import utc_now
from zenml.zen_stores.execution_archive.archiver import load_archive_payload
from zenml.zen_stores.execution_archive.capture import (
    ExecutionArchiveCapturer,
    chunked_ids,
)
from zenml.zen_stores.execution_archive.catalog import (
    ExecutionArchiveCatalog,
    ExecutionArchiveClaim,
)
from zenml.zen_stores.execution_archive.exceptions import (
    ArchiveObjectInvalidError,
    ChecksumMismatchError,
)
from zenml.zen_stores.execution_archive.payload import ExecutionArchivePayload
from zenml.zen_stores.execution_archive.payload_mover import (
    ExecutionArchivePayloadMover,
)
from zenml.zen_stores.execution_archive.storage import (
    ExecutionArchiveStorage,
    build_execution_archive_storage,
)
from zenml.zen_stores.execution_archive.worker import (
    new_execution_archive_worker_id,
)
from zenml.zen_stores.schemas import PipelineRunSchema, PipelineSnapshotSchema

if TYPE_CHECKING:
    from zenml.zen_stores.sql_zen_store import SqlZenStore

logger = get_logger(__name__)

_DEFAULT_BATCH_SIZE = 500


class ExecutionArchiveAuthority:
    """Move SQL authority to and from one verified archive object."""

    def __init__(
        self,
        *,
        store: "SqlZenStore",
        config: Optional[ServerConfiguration] = None,
        storage: Optional[ExecutionArchiveStorage] = None,
        clock: Callable[[], datetime] = utc_now,
        owner: Optional[str] = None,
        lease_seconds: float = (
            DEFAULT_ZENML_SERVER_EXECUTION_ARCHIVE_LEASE_SECONDS
        ),
        batch_size: int = _DEFAULT_BATCH_SIZE,
        compaction_enabled: Optional[bool] = None,
    ) -> None:
        """Initialize the authority service.

        Args:
            store: SQL Zen store containing execution history.
            config: Deployment archive configuration.
            storage: Injected archive storage, primarily for testing.
            clock: Source of lifecycle timestamps.
            owner: Unique worker identity.
            lease_seconds: Duration of each fenced ownership lease.
            batch_size: Maximum payload rows changed per transaction.
            compaction_enabled: Optional deployment-gate override.

        Raises:
            ValueError: If the batch size is not positive.
        """
        if batch_size <= 0:
            raise ValueError(
                "The execution archive batch size must be positive."
            )
        config = config or ServerConfiguration.get_server_config()
        self._store = store
        self._workspace_id = store.get_deployment_id()
        self._storage = storage or build_execution_archive_storage(
            config, workspace_id=self._workspace_id
        )
        self._clock = clock
        self._lease_seconds = lease_seconds
        self._batch_size = batch_size
        self._compaction_enabled = (
            config.execution_archive_compaction_enabled
            if compaction_enabled is None
            else compaction_enabled
        )
        self._owner = owner or new_execution_archive_worker_id()
        self._catalog = ExecutionArchiveCatalog(store.engine)
        self._capturer = ExecutionArchiveCapturer(store.engine)

    def compact(
        self, *, archive_id: UUID, project_id: UUID
    ) -> ExecutionArchiveResponse:
        """Make a verified archive authoritative and compact SQL payload.

        Args:
            archive_id: Generation to compact.
            project_id: Project that must own the generation.

        Returns:
            Cold archive generation.

        Raises:
            ExecutionArchiveStateError: If compaction is disabled or the
                generation cannot be compacted.
            ExecutionArchiveParityError: If SQL changed after verification.
            ArchiveUnavailableError: If the archive object cannot be trusted.
            Exception: Any storage or SQL failure after its safe catalog
                outcome is recorded.
        """
        archive = self._require_archive(archive_id, project_id)
        if archive.state == ExecutionArchiveState.COLD:
            return archive
        if (
            archive.state == ExecutionArchiveState.VERIFIED
            and not self._compaction_enabled
        ):
            raise ExecutionArchiveStateError(
                "Execution archive compaction is disabled on this server."
            )
        if archive.state not in {
            ExecutionArchiveState.VERIFIED,
            ExecutionArchiveState.COMPACTING,
        }:
            raise ExecutionArchiveStateError(
                f"Execution archive {archive_id} is {archive.state.value}; "
                "only a verified or interrupted compacting generation can "
                "be compacted."
            )
        claim = self._catalog.claim(
            archive_id,
            owner=self._owner,
            lease_seconds=self._lease_seconds,
        )
        authoritative = claim.archive.requires_restore
        try:
            if claim.archive.state not in {
                ExecutionArchiveState.VERIFIED,
                ExecutionArchiveState.COMPACTING,
                ExecutionArchiveState.COLD,
            }:
                raise ExecutionArchiveStateError(
                    f"Execution archive {archive_id} is "
                    f"{claim.archive.state.value}; only a verified or "
                    "interrupted compacting generation can be compacted."
                )
            if claim.archive.state == ExecutionArchiveState.COLD:
                return claim.archive
            payload = self._load_payload(claim.archive)
            claim = self._renew(claim)
            if claim.archive.state == ExecutionArchiveState.VERIFIED:
                self._commit_authority(claim, payload)
                authoritative = True
            self._mover().compact(claim, payload)
            return self._catalog.require(archive_id)
        except (ArchiveObjectInvalidError, ChecksumMismatchError) as error:
            self._catalog.try_record_failure(
                claim, error, state=ExecutionArchiveState.CORRUPT
            )
            raise ArchiveUnavailableError(
                f"Execution archive {archive_id} is corrupt: {error}"
            ) from error
        except ExecutionArchiveParityError as error:
            self._catalog.try_record_failure(
                claim,
                error,
                state=None if authoritative else ExecutionArchiveState.FAILED,
            )
            raise
        except ExecutionArchiveStateError:
            raise
        except Exception as error:
            self._catalog.try_record_failure(claim, error)
            raise
        finally:
            self._catalog.release(claim)

    def restore(
        self, *, archive_id: UUID, project_id: UUID
    ) -> ExecutionArchiveResponse:
        """Restore SQL payload and return authority to SQL.

        Args:
            archive_id: Generation to restore.
            project_id: Project that must own the generation.

        Returns:
            Restored archive generation.

        Raises:
            ExecutionArchiveStateError: If the generation owns no SQL payload.
            ArchiveUnavailableError: If the archive object cannot be trusted.
            Exception: Any storage or SQL failure after its safe catalog
                outcome is recorded.
        """
        archive = self._require_archive(archive_id, project_id)
        if archive.state == ExecutionArchiveState.RESTORED:
            return archive
        if not archive.requires_restore:
            raise ExecutionArchiveStateError(
                f"Execution archive {archive_id} is {archive.state.value} "
                "and owns no SQL payload to restore."
            )
        claim = self._catalog.claim(
            archive_id,
            owner=self._owner,
            lease_seconds=self._lease_seconds,
        )
        try:
            if not claim.archive.requires_restore:
                raise ExecutionArchiveStateError(
                    f"Execution archive {archive_id} no longer requires "
                    "restoration."
                )
            payload = self._load_payload(claim.archive)
            claim = self._renew(claim)
            self._start_restore(claim)
            self._mover().restore(claim, payload)
            self._finish_restore(claim, payload)
            return self._catalog.require(archive_id)
        except (ArchiveObjectInvalidError, ChecksumMismatchError) as error:
            self._catalog.try_record_failure(
                claim, error, state=ExecutionArchiveState.CORRUPT
            )
            raise ArchiveUnavailableError(
                f"Execution archive {archive_id} is corrupt: {error}"
            ) from error
        except ExecutionArchiveStateError:
            raise
        except Exception as error:
            self._catalog.try_record_failure(claim, error)
            raise
        finally:
            self._catalog.release(claim)

    def _require_archive(
        self, archive_id: UUID, project_id: UUID
    ) -> ExecutionArchiveResponse:
        archive = self._catalog.get(archive_id, project_id=project_id)
        if archive is None:
            raise DoesNotExistException(
                f"Execution archive {archive_id} does not exist in project "
                f"{project_id}."
            )
        return archive

    def _load_payload(
        self, archive: ExecutionArchiveResponse
    ) -> ExecutionArchivePayload:
        return load_archive_payload(
            storage=self._storage,
            object_key=self._catalog.object_key(archive.id),
            archive=archive,
            workspace_id=self._workspace_id,
        )

    def _renew(self, claim: ExecutionArchiveClaim) -> ExecutionArchiveClaim:
        return self._catalog.renew(claim, lease_seconds=self._lease_seconds)

    def _mover(self) -> "ExecutionArchivePayloadMover":
        return ExecutionArchivePayloadMover(
            self._store.engine,
            catalog=self._catalog,
            batch_size=self._batch_size,
            lease_seconds=self._lease_seconds,
            clock=self._clock,
        )

    def _commit_authority(
        self,
        claim: ExecutionArchiveClaim,
        payload: ExecutionArchivePayload,
    ) -> None:
        with Session(self._store.engine) as session:
            schema = self._catalog.require_claimed(session, claim)
            if schema.archive_state != ExecutionArchiveState.VERIFIED:
                raise ExecutionArchiveStateError(
                    f"Execution archive {schema.id} is {schema.state}; "
                    "authority can only move from a verified generation."
                )
            capture = self._capturer.capture(
                project_id=schema.project_id,
                root_run_id=schema.root_run_id,
                session=session,
                for_update=True,
            )
            if capture.source_fingerprint != payload.source_fingerprint:
                raise ExecutionArchiveParityError(
                    "The execution tree changed after its archive was "
                    "verified. Export a new generation before compacting."
                )
            _require_unmarked_tree(
                session,
                archive_id=schema.id,
                run_ids=capture.family.run_ids,
                snapshot_ids=capture.family.snapshot_ids,
            )
            for ids in chunked_ids(capture.family.run_ids):
                session.execute(
                    update(PipelineRunSchema)
                    .where(col(PipelineRunSchema.id).in_(ids))
                    .values(execution_archive_id=schema.id)
                )
            for ids in chunked_ids(capture.family.snapshot_ids):
                session.execute(
                    update(PipelineSnapshotSchema)
                    .where(col(PipelineSnapshotSchema.id).in_(ids))
                    .values(execution_archive_id=schema.id)
                )
            self._catalog.transition(
                session,
                claim,
                ExecutionArchiveState.COMPACTING,
                committed_at=self._clock(),
            )
            session.commit()

    def _start_restore(self, claim: ExecutionArchiveClaim) -> None:
        with Session(self._store.engine) as session:
            self._catalog.transition(
                session, claim, ExecutionArchiveState.RESTORING
            )
            session.commit()

    def _finish_restore(
        self,
        claim: ExecutionArchiveClaim,
        payload: ExecutionArchivePayload,
    ) -> None:
        run_ids = [record.id for record in payload.runs]
        snapshot_ids = [record.id for record in payload.snapshots]
        with Session(self._store.engine) as session:
            schema = self._catalog.require_claimed(session, claim)
            if schema.archive_state != ExecutionArchiveState.RESTORING:
                raise ExecutionArchiveStateError(
                    f"Execution archive {schema.id} is {schema.state}; "
                    "restoration cannot be completed."
                )
            _require_owned_markers(
                session,
                archive_id=schema.id,
                run_ids=run_ids,
                snapshot_ids=snapshot_ids,
            )
            for ids in chunked_ids(run_ids):
                session.execute(
                    update(PipelineRunSchema)
                    .where(col(PipelineRunSchema.id).in_(ids))
                    .where(
                        col(PipelineRunSchema.execution_archive_id)
                        == schema.id
                    )
                    .values(execution_archive_id=None)
                )
            for ids in chunked_ids(snapshot_ids):
                session.execute(
                    update(PipelineSnapshotSchema)
                    .where(col(PipelineSnapshotSchema.id).in_(ids))
                    .where(
                        col(PipelineSnapshotSchema.execution_archive_id)
                        == schema.id
                    )
                    .values(execution_archive_id=None)
                )
            self._catalog.transition(
                session,
                claim,
                ExecutionArchiveState.RESTORED,
                restored_at=self._clock(),
            )
            session.commit()


def _require_unmarked_tree(
    session: Session,
    *,
    archive_id: UUID,
    run_ids: Sequence[UUID],
    snapshot_ids: Sequence[UUID],
) -> None:
    for table, ids in (
        (PipelineSnapshotSchema, snapshot_ids),
        (PipelineRunSchema, run_ids),
    ):
        for chunk in chunked_ids(ids):
            marker = session.exec(
                select(table.execution_archive_id)
                .where(col(table.id).in_(chunk))
                .where(col(table.execution_archive_id).is_not(None))
                .limit(1)
            ).first()
            if marker is not None:
                raise ExecutionArchiveStateError(
                    "Another archive already owns part of execution archive "
                    f"{archive_id}."
                )


def _require_owned_markers(
    session: Session,
    *,
    archive_id: UUID,
    run_ids: Sequence[UUID],
    snapshot_ids: Sequence[UUID],
) -> None:
    for table, ids in (
        (PipelineSnapshotSchema, snapshot_ids),
        (PipelineRunSchema, run_ids),
    ):
        for chunk in chunked_ids(ids):
            markers = session.exec(
                select(table.execution_archive_id)
                .where(col(table.id).in_(chunk))
                .with_for_update()
            ).all()
            if any(marker != archive_id for marker in markers):
                raise ExecutionArchiveStateError(
                    f"Execution archive {archive_id} lost one of its SQL "
                    "markers."
                )
