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
"""Bounded SQL payload movement for authoritative execution archives."""

import json
from datetime import datetime
from typing import (
    Callable,
    Dict,
    Iterable,
    List,
    Optional,
    Sequence,
    Type,
    TypeVar,
)
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy.engine import Engine
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.base import ExecutableOption
from sqlmodel import Session, col, select

from zenml.enums import ExecutionArchiveState
from zenml.exceptions import (
    ExecutionArchiveParityError,
    ExecutionArchiveStateError,
)
from zenml.zen_stores.execution_archive.catalog import (
    ExecutionArchiveCatalog,
    ExecutionArchiveClaim,
)
from zenml.zen_stores.execution_archive.payload import (
    ARCHIVED_CONFIGURATION_FIELDS,
    ARCHIVED_RUN_FIELDS,
    ARCHIVED_SNAPSHOT_FIELDS,
    ARCHIVED_STEP_FIELDS,
    ExecutionArchivePayload,
)
from zenml.zen_stores.execution_archive_utils import (
    archived_payload_placeholder,
)
from zenml.zen_stores.schemas import (
    BaseSchema,
    PipelineRunSchema,
    PipelineSnapshotSchema,
    StepConfigurationSchema,
    StepRunSchema,
)
from zenml.zen_stores.schemas.utils import jl_arg

S = TypeVar("S", bound=BaseSchema)


class ExecutionArchivePayloadMover:
    """Replace and restore archived fields in bounded transactions."""

    def __init__(
        self,
        engine: Engine,
        *,
        catalog: ExecutionArchiveCatalog,
        batch_size: int,
        lease_seconds: float,
        clock: Callable[[], datetime],
    ) -> None:
        """Initialize the payload mover.

        Args:
            engine: SQL store engine.
            catalog: Archive catalog owning state transitions.
            batch_size: Maximum rows changed per transaction.
            lease_seconds: Claim renewal duration.
            clock: Source of lifecycle timestamps.
        """
        self._engine = engine
        self._catalog = catalog
        self._batch_size = batch_size
        self._lease_seconds = lease_seconds
        self._clock = clock

    def compact(
        self, claim: ExecutionArchiveClaim, payload: ExecutionArchivePayload
    ) -> None:
        """Replace the generation's payload fields with typed placeholders.

        Args:
            claim: Current fenced ownership.
            payload: Verified source payload.
        """
        self._move(
            claim,
            payload,
            state=ExecutionArchiveState.COMPACTING,
            compact=True,
        )
        with Session(self._engine) as session:
            self._catalog.transition(
                session,
                claim,
                ExecutionArchiveState.COLD,
                compacted_at=self._clock(),
            )
            session.commit()

    def restore(
        self, claim: ExecutionArchiveClaim, payload: ExecutionArchivePayload
    ) -> None:
        """Restore the generation's payload fields from its object.

        Rows deleted after compaction are intentionally skipped.

        Args:
            claim: Current fenced ownership.
            payload: Verified source payload.
        """
        self._move(
            claim,
            payload,
            state=ExecutionArchiveState.RESTORING,
            compact=False,
        )

    def _move(
        self,
        claim: ExecutionArchiveClaim,
        payload: ExecutionArchivePayload,
        *,
        state: ExecutionArchiveState,
        compact: bool,
    ) -> None:
        write = _compact_fields if compact else _restore_fields
        self._write_rows(
            claim,
            state,
            StepRunSchema,
            {record.id: record for record in payload.steps},
            ARCHIVED_STEP_FIELDS,
            write,
            before=_store_step_projection if compact else None,
            options=(
                selectinload(jl_arg(StepRunSchema.snapshot)),
                selectinload(jl_arg(StepRunSchema.static_config)),
                selectinload(jl_arg(StepRunSchema.dynamic_config)),
                selectinload(jl_arg(StepRunSchema.pipeline_run)),
            ),
        )
        self._write_rows(
            claim,
            state,
            PipelineRunSchema,
            {record.id: record for record in payload.runs},
            ARCHIVED_RUN_FIELDS,
            write,
        )
        self._write_rows(
            claim,
            state,
            StepConfigurationSchema,
            {record.id: record for record in payload.step_configurations},
            ARCHIVED_CONFIGURATION_FIELDS,
            write,
        )
        self._write_rows(
            claim,
            state,
            PipelineSnapshotSchema,
            {record.id: record for record in payload.snapshots},
            ARCHIVED_SNAPSHOT_FIELDS,
            write,
        )

    def _write_rows(
        self,
        claim: ExecutionArchiveClaim,
        state: ExecutionArchiveState,
        table: Type[S],
        records: Dict[UUID, BaseModel],
        fields: Sequence[str],
        write: Callable[[BaseSchema, BaseModel, Sequence[str], UUID], None],
        *,
        before: Optional[Callable[[S], None]] = None,
        options: Sequence[ExecutableOption] = (),
    ) -> None:
        for ids in _batches(records, self._batch_size):
            with Session(self._engine) as session:
                schema = self._catalog.require_claimed(session, claim)
                if schema.archive_state != state:
                    raise ExecutionArchiveStateError(
                        f"Execution archive {schema.id} is {schema.state}; "
                        f"expected {state.value}."
                    )
                rows = session.exec(
                    select(table)
                    .where(col(table.id).in_(ids))
                    .options(*options)
                    .with_for_update()
                ).all()
                for row in rows:
                    if before is not None:
                        before(row)
                    write(row, records[row.id], fields, claim.archive_id)
                    session.add(row)
                session.commit()
            self._catalog.renew(claim, lease_seconds=self._lease_seconds)


def _compact_fields(
    row: BaseSchema,
    record: BaseModel,
    fields: Sequence[str],
    archive_id: UUID,
) -> None:
    placeholder = archived_payload_placeholder(archive_id)
    for field in fields:
        current = getattr(row, field)
        expected = getattr(record, field)
        if current == placeholder or current is None and expected is None:
            continue
        if current != expected:
            raise ExecutionArchiveParityError(
                f"{type(row).__name__} {row.id} field '{field}' changed "
                "after the archive authority switch."
            )
        setattr(row, field, placeholder)


def _restore_fields(
    row: BaseSchema,
    record: BaseModel,
    fields: Sequence[str],
    archive_id: UUID,
) -> None:
    placeholder = archived_payload_placeholder(archive_id)
    for field in fields:
        current = getattr(row, field)
        expected = getattr(record, field)
        if current == expected:
            continue
        if current != placeholder:
            raise ExecutionArchiveParityError(
                f"{type(row).__name__} {row.id} field '{field}' does not "
                "belong to execution archive restoration."
            )
        setattr(row, field, expected)


def _store_step_projection(step: StepRunSchema) -> None:
    if step.step_type is not None and step.substitutions is not None:
        return
    configuration = step.get_step_configuration()
    if step.step_type is None:
        step.step_type = (
            configuration.config.step_type.value
            if configuration.config.step_type
            else None
        )
    if step.substitutions is None:
        step.substitutions = json.dumps(
            configuration.config.substitutions, sort_keys=True
        )


def _batches(values: Iterable[UUID], size: int) -> List[List[UUID]]:
    ordered = list(values)
    return [
        ordered[index : index + size] for index in range(0, len(ordered), size)
    ]
