#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Two-phase, idempotent execution archive purge."""

from datetime import datetime
from typing import Callable, List, Optional
from uuid import UUID

from sqlalchemy import update
from sqlalchemy.engine import Engine
from sqlmodel import Session, col, select

from zenml.constants import (
    DEFAULT_ZENML_SERVER_EXECUTION_ARCHIVE_LEASE_SECONDS,
)
from zenml.exceptions import (
    DoesNotExistException,
    ExecutionArchiveStateError,
)
from zenml.models import ExecutionArchiveResponse
from zenml.utils.time_utils import utc_now
from zenml.zen_stores.execution_archive.catalog import (
    ExecutionArchiveCatalog,
    ExecutionArchiveClaim,
)
from zenml.zen_stores.execution_archive.storage import ExecutionArchiveStorage
from zenml.zen_stores.execution_archive.worker import (
    new_execution_archive_worker_id,
)
from zenml.zen_stores.schemas import (
    ExecutionArchiveSchema,
    ProjectSchema,
)


class ExecutionArchivePurger:
    """Queue and drain object deletion without blocking project deletion."""

    def __init__(
        self,
        engine: Engine,
        *,
        storage: Optional[ExecutionArchiveStorage] = None,
        clock: Callable[[], datetime] = utc_now,
        owner: Optional[str] = None,
        lease_seconds: float = (
            DEFAULT_ZENML_SERVER_EXECUTION_ARCHIVE_LEASE_SECONDS
        ),
    ) -> None:
        """Initialize the purger.

        Args:
            engine: SQL store engine.
            storage: Configured object storage, required for stored objects.
            clock: Source of lifecycle timestamps.
            owner: Unique worker identity.
            lease_seconds: Duration of each fenced purge claim.
        """
        self._engine = engine
        self._storage = storage
        self._clock = clock
        self._lease_seconds = lease_seconds
        self._owner = owner or new_execution_archive_worker_id()
        self._catalog = ExecutionArchiveCatalog(engine)

    def request(
        self, *, archive_id: UUID, project_id: UUID
    ) -> ExecutionArchiveResponse:
        """Queue a safe generation for asynchronous purge.

        An archive that owns payload for an existing project must be restored
        first. Project deletion uses `mark_project` in the same SQL transaction
        and is allowed to queue every generation because its SQL rows are being
        deleted too.

        Args:
            archive_id: Generation to purge.
            project_id: Project that must own the generation.

        Returns:
            Generation with its purge timestamp.

        Raises:
            DoesNotExistException: If the generation does not belong to the
                project.
            ExecutionArchiveStateError: If its object is authoritative for a
                live project.
        """
        with Session(self._engine) as session:
            schema = session.exec(
                select(ExecutionArchiveSchema)
                .where(col(ExecutionArchiveSchema.id) == archive_id)
                .where(col(ExecutionArchiveSchema.project_id) == project_id)
                .with_for_update()
            ).one_or_none()
            if schema is None:
                raise DoesNotExistException(
                    f"Execution archive {archive_id} does not exist in "
                    f"project {project_id}."
                )
            if schema.requires_restore and _project_exists(
                session, project_id
            ):
                raise ExecutionArchiveStateError(
                    f"Restore execution archive {archive_id} before purging "
                    "its authoritative object."
                )
            if schema.purge_pending_at is None:
                now = self._clock()
                schema.purge_pending_at = now
                schema.updated = now
                session.add(schema)
                session.commit()
                session.refresh(schema)
            return schema.to_model()

    @staticmethod
    def mark_project(session: Session, project_id: UUID) -> None:
        """Queue every project generation inside the deletion transaction.

        Args:
            session: Project-deletion transaction.
            project_id: Project being deleted.
        """
        now = utc_now()
        session.execute(
            update(ExecutionArchiveSchema)
            .where(col(ExecutionArchiveSchema.project_id) == project_id)
            .where(col(ExecutionArchiveSchema.purge_pending_at).is_(None))
            .values(purge_pending_at=now, updated=now)
        )

    def pending_ids(self, *, limit: int) -> List[UUID]:
        """Return the oldest queued generation IDs.

        Args:
            limit: Maximum IDs returned.

        Returns:
            Oldest purge requests first.
        """
        with Session(self._engine) as session:
            return list(
                session.exec(
                    select(ExecutionArchiveSchema.id)
                    .where(
                        col(ExecutionArchiveSchema.purge_pending_at).is_not(
                            None
                        )
                    )
                    .order_by(
                        col(ExecutionArchiveSchema.updated),
                        col(ExecutionArchiveSchema.id),
                    )
                    .limit(limit)
                ).all()
            )

    def purge(self, archive_id: UUID) -> None:
        """Delete one queued object and then its catalog row idempotently.

        Args:
            archive_id: Queued generation ID.

        Raises:
            ExecutionArchiveStateError: If the generation is not purgeable or
                the configured target differs.
            Exception: If object or catalog deletion fails.
        """
        claim = self._catalog.claim(
            archive_id,
            owner=self._owner,
            lease_seconds=self._lease_seconds,
        )
        deleted = False
        try:
            self._validate(claim)
            if self._storage is None:
                raise ExecutionArchiveStateError(
                    "Archive storage is required to purge a generation."
                )
            if (
                self._storage.target_digest
                != claim.archive.storage_target_digest
            ):
                raise ExecutionArchiveStateError(
                    "The configured archive target differs from the "
                    "generation queued for purge."
                )
            self._storage.delete_generation(
                project_id=claim.archive.project_id,
                archive_id=claim.archive_id,
            )
            with Session(self._engine) as session:
                schema = self._catalog.require_claimed(session, claim)
                self._require_purgeable(session, schema)
                session.delete(schema)
                session.commit()
                deleted = True
        except Exception as error:
            self._catalog.try_record_failure(claim, error)
            raise
        finally:
            if not deleted:
                self._catalog.release(claim)

    def _validate(self, claim: ExecutionArchiveClaim) -> None:
        with Session(self._engine) as session:
            schema = self._catalog.require_claimed(session, claim)
            self._require_purgeable(session, schema)

    @staticmethod
    def _require_purgeable(
        session: Session, schema: ExecutionArchiveSchema
    ) -> None:
        if schema.purge_pending_at is None:
            raise ExecutionArchiveStateError(
                f"Execution archive {schema.id} is not queued for purge."
            )
        if schema.requires_restore and _project_exists(
            session, schema.project_id
        ):
            raise ExecutionArchiveStateError(
                f"Execution archive {schema.id} still owns SQL payload."
            )


def _project_exists(session: Session, project_id: UUID) -> bool:
    return (
        session.exec(
            select(ProjectSchema.id).where(col(ProjectSchema.id) == project_id)
        ).one_or_none()
        is not None
    )
