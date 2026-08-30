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
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
#  implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""The archive catalog: every state transition of an archive generation.

States and their edges:

    EXPORTING ──► VERIFIED ──► COMPACTING ──► COLD ──► RESTORING ──► RESTORED
        │            │                          │
        ├──► FAILED ◄┘                          └──► COLD  (retry)
        └──► CORRUPT
      FAILED ──► EXPORTING  (retry)

SQL payload is authoritative through `VERIFIED`; the archive is
authoritative from `COMPACTING` until `RESTORED`. The edges live here:
callers name the state they want to reach and the catalog decides whether
the row may move there, and refuses a second authoritative generation for a
family. Work that spans several transactions claims the generation first,
so two workers never move the same generation at once.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, FrozenSet, Iterable, List, Optional
from uuid import UUID

from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, desc, select

from zenml.enums import ExecutionArchiveState
from zenml.models import ExecutionArchiveObject, ExecutionArchiveResponse
from zenml.utils.time_utils import utc_now
from zenml.zen_stores.execution_archive.exceptions import (
    ExecutionArchiveStateError,
)
from zenml.zen_stores.schemas import ExecutionArchiveSchema

S = ExecutionArchiveState
# A state maps to itself where work in that state is done in batches: the
# self-transition is the locked check that nothing moved the row meanwhile.
TRANSITIONS: Dict[S, FrozenSet[S]] = {
    S.EXPORTING: frozenset({S.EXPORTING, S.VERIFIED, S.FAILED, S.CORRUPT}),
    S.VERIFIED: frozenset({S.VERIFIED, S.COMPACTING, S.FAILED, S.CORRUPT}),
    S.FAILED: frozenset({S.EXPORTING}),
    S.COMPACTING: frozenset({S.COMPACTING, S.COLD, S.RESTORING}),
    S.COLD: frozenset({S.COLD, S.RESTORING}),
    S.RESTORING: frozenset({S.RESTORING, S.RESTORED, S.COLD}),
    S.RESTORED: frozenset(),
    S.CORRUPT: frozenset(),
}
RESUMABLE_EXPORT_STATES = frozenset({S.EXPORTING, S.VERIFIED, S.FAILED})
AUTHORITATIVE_STATE_VALUES = [
    state.value for state in S if state.is_authoritative
]


class ExecutionArchiveCatalog:
    """Reads and writes `execution_archive` rows."""

    def __init__(self, engine: Engine) -> None:
        """Initialize the catalog.

        Args:
            engine: The SQL store engine.
        """
        self._engine = engine

    def begin_export(
        self,
        *,
        project_id: UUID,
        root_run_id: UUID,
        generation: int,
        source_fingerprint: str,
        storage_target_id: UUID,
        stored_bytes: int,
    ) -> ExecutionArchiveResponse:
        """Create a generation, or resume one that was not verified yet.

        Args:
            project_id: The project of the family.
            root_run_id: The root run of the family.
            generation: The generation number.
            source_fingerprint: Fingerprint of the captured family.
            storage_target_id: The target the objects are written to.
            stored_bytes: Bytes the family's payload holds in the database.

        Returns:
            The generation in `EXPORTING` or `VERIFIED`.

        Raises:
            ExecutionArchiveStateError: If the generation exists for another
                family, payload or state.
        """
        with Session(self._engine) as session:
            schema = self._generation_for_update(
                session, root_run_id, generation
            )
            if schema is None:
                schema = ExecutionArchiveSchema(
                    project_id=project_id,
                    root_run_id=root_run_id,
                    generation=generation,
                    state=S.EXPORTING.value,
                    source_fingerprint=source_fingerprint,
                    storage_target_id=storage_target_id,
                    stored_bytes=stored_bytes,
                )
                session.add(schema)
                try:
                    session.commit()
                except IntegrityError:
                    # Another worker created the generation first; resume it.
                    session.rollback()
                    schema = self._generation_for_update(
                        session, root_run_id, generation
                    )
                    if schema is None:
                        raise
            if (
                schema.project_id != project_id
                or schema.source_fingerprint != source_fingerprint
            ):
                raise ExecutionArchiveStateError(
                    "The project or payload changed; archive the family as "
                    "a new generation."
                )
            if schema.archive_state not in RESUMABLE_EXPORT_STATES:
                raise ExecutionArchiveStateError(
                    f"Execution archive {schema.id} is {schema.state} and "
                    "cannot be exported again."
                )
            if schema.archive_state == S.FAILED:
                schema.state = S.EXPORTING.value
                schema.last_error = None
                schema.updated = utc_now()
                session.add(schema)
                session.commit()
            return schema.to_model()

    def record_objects(
        self,
        archive_id: UUID,
        *,
        manifest: ExecutionArchiveObject,
        execution: ExecutionArchiveObject,
        snapshots: ExecutionArchiveObject,
    ) -> ExecutionArchiveResponse:
        """Record the objects an export wrote.

        Args:
            archive_id: The generation.
            manifest: The manifest object.
            execution: The execution payload object.
            snapshots: The snapshot payload object.

        Returns:
            The generation with its objects.
        """
        with Session(self._engine) as session:
            schema = self.transition(session, archive_id, S.EXPORTING)
            schema.set_objects(
                manifest=manifest, execution=execution, snapshots=snapshots
            )
            session.add(schema)
            session.commit()
            return schema.to_model()

    def mark_verified(self, archive_id: UUID) -> None:
        """Record that the objects were read back and match SQL.

        Args:
            archive_id: The generation.
        """
        with Session(self._engine) as session:
            self.transition(session, archive_id, S.VERIFIED)
            session.commit()

    def mark_failed(self, archive_id: UUID, state: S, error: str) -> None:
        """Record that an export or a switch failed.

        Args:
            archive_id: The generation.
            state: `FAILED` for a retryable failure, `CORRUPT` when the
                stored objects do not match their digests.
            error: What went wrong.
        """
        with Session(self._engine) as session:
            self.transition(session, archive_id, state, last_error=error)
            session.commit()

    def record_error(self, archive_id: UUID, error: str) -> None:
        """Record an error that leaves the generation in its state.

        Args:
            archive_id: The generation.
            error: What went wrong.
        """
        with Session(self._engine) as session:
            schema = self.lock(session, archive_id)
            schema.last_error = error
            schema.updated = utc_now()
            session.add(schema)
            session.commit()

    def claim(
        self, archive_id: UUID, *, owner: str, seconds: float
    ) -> ExecutionArchiveResponse:
        """Take or renew ownership of a generation for a while.

        Args:
            archive_id: The generation.
            owner: The worker claiming it.
            seconds: How long the claim lasts unless renewed.

        Returns:
            The claimed generation.

        Raises:
            ExecutionArchiveStateError: If another worker holds a live
                claim.
        """
        now = utc_now()
        with Session(self._engine) as session:
            schema = self.lock(session, archive_id)
            if (
                schema.owner not in (None, owner)
                and schema.owner_expires_at is not None
                and schema.owner_expires_at > now
            ):
                raise ExecutionArchiveStateError(
                    f"Execution archive {archive_id} is being processed by "
                    f"{schema.owner}."
                )
            schema.owner = owner
            schema.owner_expires_at = now + timedelta(seconds=seconds)
            session.add(schema)
            session.commit()
            return schema.to_model()

    def renew(self, archive_id: UUID, *, owner: str, seconds: float) -> bool:
        """Extend a claim if this worker still holds it.

        Args:
            archive_id: The generation.
            owner: The worker renewing it.
            seconds: How long the renewed claim lasts.

        Returns:
            Whether the claim was still held and is now renewed.
        """
        with Session(self._engine) as session:
            schema = self.lock(session, archive_id)
            if schema.owner != owner:
                return False
            schema.owner_expires_at = utc_now() + timedelta(seconds=seconds)
            session.add(schema)
            session.commit()
            return True

    def release(self, archive_id: UUID, *, owner: str) -> None:
        """Give up a claim.

        Args:
            archive_id: The generation.
            owner: The worker releasing it.
        """
        with Session(self._engine) as session:
            schema = self.lock(session, archive_id)
            if schema.owner == owner:
                schema.owner = None
                schema.owner_expires_at = None
                session.add(schema)
                session.commit()

    @staticmethod
    def transition(
        session: Session,
        archive_id: UUID,
        to: S,
        *,
        committed_at: Optional[datetime] = None,
        compacted_at: Optional[datetime] = None,
        restored_at: Optional[datetime] = None,
        last_error: Optional[str] = None,
    ) -> ExecutionArchiveSchema:
        """Move a generation along one edge of the state graph.

        The row is locked for the rest of the transaction. Moving to the
        state the row is in already is allowed where work in that state is
        batched: it is the locked check that the state still holds.

        Args:
            session: The transaction.
            archive_id: The generation.
            to: The target state.
            committed_at: When the archive became authoritative.
            compacted_at: When the payload left SQL.
            restored_at: When the payload returned to SQL.
            last_error: The error to record.

        Returns:
            The locked, updated row.

        Raises:
            ExecutionArchiveStateError: If the edge does not exist or
                another generation of the family is authoritative.
        """
        schema = ExecutionArchiveCatalog.lock(session, archive_id)
        if to not in TRANSITIONS[schema.archive_state]:
            raise ExecutionArchiveStateError(
                f"Execution archive {archive_id} is {schema.state} and "
                f"cannot become {to.value}."
            )
        if to.is_authoritative and not schema.archive_state.is_authoritative:
            other = session.exec(
                select(ExecutionArchiveSchema.id)
                .where(
                    col(ExecutionArchiveSchema.root_run_id)
                    == schema.root_run_id
                )
                .where(col(ExecutionArchiveSchema.id) != archive_id)
                .where(
                    col(ExecutionArchiveSchema.state).in_(
                        AUTHORITATIVE_STATE_VALUES
                    )
                )
                .with_for_update()
            ).first()
            if other is not None:
                raise ExecutionArchiveStateError(
                    f"Execution archive {other} is already authoritative "
                    "for this execution family."
                )
        schema.state = to.value
        if committed_at is not None:
            schema.committed_at = committed_at
        if compacted_at is not None:
            schema.compacted_at = compacted_at
        if restored_at is not None:
            schema.restored_at = restored_at
        if last_error is not None:
            schema.last_error = last_error
        schema.updated = utc_now()
        session.add(schema)
        return schema

    @staticmethod
    def lock(session: Session, archive_id: UUID) -> ExecutionArchiveSchema:
        """Load a generation with a row lock.

        Args:
            session: The transaction.
            archive_id: The generation.

        Returns:
            The locked row.

        Raises:
            ExecutionArchiveStateError: If the generation does not exist.
        """
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

    def get(
        self, archive_id: UUID, project_id: Optional[UUID] = None
    ) -> Optional[ExecutionArchiveResponse]:
        """Load a generation.

        Args:
            archive_id: The generation.
            project_id: If given, the project the generation must belong to.

        Returns:
            The generation, or None if it does not exist in the project.
        """
        statement = select(ExecutionArchiveSchema).where(
            col(ExecutionArchiveSchema.id) == archive_id
        )
        if project_id is not None:
            statement = statement.where(
                col(ExecutionArchiveSchema.project_id) == project_id
            )
        return self._first(statement)

    def require(self, archive_id: UUID) -> ExecutionArchiveResponse:
        """Load a generation that is known to exist.

        Args:
            archive_id: The generation.

        Returns:
            The generation.

        Raises:
            ExecutionArchiveStateError: If the generation does not exist.
        """
        archive = self.get(archive_id)
        if archive is None:
            raise ExecutionArchiveStateError(
                f"Execution archive {archive_id} does not exist."
            )
        return archive

    def latest_for_root(
        self, root_run_id: UUID
    ) -> Optional[ExecutionArchiveResponse]:
        """Load the newest generation of a family.

        Args:
            root_run_id: The root run of the family.

        Returns:
            The generation, or None if the family was never archived.
        """
        return self._first(
            select(ExecutionArchiveSchema)
            .where(col(ExecutionArchiveSchema.root_run_id) == root_run_id)
            .order_by(desc(col(ExecutionArchiveSchema.generation)))
        )

    @staticmethod
    def authoritative(
        session: Session,
        *,
        root_run_ids: Iterable[UUID] = (),
        archive_ids: Iterable[UUID] = (),
    ) -> List[ExecutionArchiveResponse]:
        """Load authoritative generations of some families or by ID.

        Args:
            session: The SQL session.
            root_run_ids: Families whose authoritative generation to load.
            archive_ids: Generations to load if they are authoritative.

        Returns:
            The matching authoritative generations; both filters combine.
        """
        root_run_ids, archive_ids = list(root_run_ids), list(archive_ids)
        if not root_run_ids and not archive_ids:
            return []
        statement = select(ExecutionArchiveSchema).where(
            col(ExecutionArchiveSchema.state).in_(AUTHORITATIVE_STATE_VALUES)
        )
        if root_run_ids:
            statement = statement.where(
                col(ExecutionArchiveSchema.root_run_id).in_(root_run_ids)
            )
        if archive_ids:
            statement = statement.where(
                col(ExecutionArchiveSchema.id).in_(archive_ids)
            )
        return [schema.to_model() for schema in session.exec(statement).all()]

    def _first(self, statement: Any) -> Optional[ExecutionArchiveResponse]:
        with Session(self._engine) as session:
            schema = session.exec(statement.limit(1)).first()
            return schema.to_model() if schema else None

    @staticmethod
    def _generation_for_update(
        session: Session, root_run_id: UUID, generation: int
    ) -> Optional[ExecutionArchiveSchema]:
        return session.exec(
            select(ExecutionArchiveSchema)
            .where(col(ExecutionArchiveSchema.root_run_id) == root_run_id)
            .where(col(ExecutionArchiveSchema.generation) == generation)
            .with_for_update()
        ).one_or_none()
