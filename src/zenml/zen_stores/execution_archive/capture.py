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
"""Bounded capture of one immutable execution tree from SQL."""

from contextlib import nullcontext
from dataclasses import dataclass
from datetime import datetime
from typing import Any, ContextManager, Iterable, List, Optional, Sequence, Set
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func
from sqlalchemy import select as sa_select
from sqlalchemy.engine import Engine
from sqlmodel import Session, and_, col, or_, select

from zenml.constants import (
    DEFAULT_ZENML_SERVER_EXECUTION_ARCHIVE_MAX_DECODED_BYTES,
    DEFAULT_ZENML_SERVER_EXECUTION_ARCHIVE_MAX_ROWS,
)
from zenml.enums import (
    ExecutionStatus,
    ResourceRequestStatus,
    RunWaitConditionStatus,
    ServiceState,
)
from zenml.exceptions import (
    ExecutionArchiveError,
    ExecutionArchiveNotEligibleError,
)
from zenml.zen_stores.execution_archive.payload import (
    ARCHIVED_CONFIGURATION_FIELDS,
    ARCHIVED_RUN_FIELDS,
    ARCHIVED_SNAPSHOT_FIELDS,
    ARCHIVED_STEP_FIELDS,
    ArchivedPipelineRunPayload,
    ArchivedPipelineSnapshotPayload,
    ArchivedStepConfigurationPayload,
    ArchivedStepRunPayload,
    ExecutionArchivePayload,
    execution_archive_source_fingerprint,
)
from zenml.zen_stores.execution_archive_utils import require_active_payload
from zenml.zen_stores.schemas import (
    DeploymentSchema,
    HookInvocationSchema,
    PipelineRunSchema,
    PipelineSnapshotSchema,
    ResourceRequestSchema,
    RunTemplateSchema,
    RunWaitConditionSchema,
    ServiceSchema,
    StepConfigurationSchema,
    StepRunSchema,
    TriggerSnapshotSchema,
)

_ID_CHUNK_SIZE = 500


class ExecutionArchiveFamily(BaseModel):
    """Identity, size, and safety evidence for one execution tree."""

    project_id: UUID
    root_run_id: UUID
    run_ids: List[UUID]
    step_run_ids: List[UUID]
    snapshot_ids: List[UUID]
    configuration_ids: List[UUID]
    source_bytes: int
    latest_mutation: datetime
    completed_at: Optional[datetime]
    blockers: List[str] = Field(default_factory=list)

    model_config = ConfigDict(frozen=True)

    @property
    def row_count(self) -> int:
        """Return the number of payload-bearing rows.

        Returns:
            Number of rows represented by the execution tree.
        """
        return (
            len(self.run_ids)
            + len(self.step_run_ids)
            + len(self.snapshot_ids)
            + len(self.configuration_ids)
        )

    def require_exportable(self) -> None:
        """Reject execution trees that cannot safely become cold later.

        Raises:
            ExecutionArchiveNotEligibleError: If a safety condition failed.
        """
        if self.blockers:
            raise ExecutionArchiveNotEligibleError(
                "The execution tree cannot be archived: "
                + "; ".join(self.blockers)
                + "."
            )


class ExecutionArchiveCapture(BaseModel):
    """One complete execution tree represented by archive payload records."""

    family: ExecutionArchiveFamily
    runs: List[ArchivedPipelineRunPayload]
    steps: List[ArchivedStepRunPayload]
    snapshots: List[ArchivedPipelineSnapshotPayload]
    step_configurations: List[ArchivedStepConfigurationPayload]
    source_fingerprint: str

    model_config = ConfigDict(frozen=True)

    def to_payload(
        self,
        *,
        archive_id: UUID,
        workspace_id: UUID,
        generation: int,
        writer_version: str,
        writer_alembic_revision: str,
        created_at: datetime,
    ) -> ExecutionArchivePayload:
        """Bind source records to one archive generation.

        Args:
            archive_id: Catalog generation ID.
            workspace_id: Immutable deployment namespace.
            generation: Generation number for the root run.
            writer_version: ZenML version writing the object.
            writer_alembic_revision: Database revision writing the object.
            created_at: Object creation time.

        Returns:
            Self-describing archive payload.
        """
        return ExecutionArchivePayload(
            archive_id=archive_id,
            workspace_id=workspace_id,
            project_id=self.family.project_id,
            root_run_id=self.family.root_run_id,
            generation=generation,
            writer_version=writer_version,
            writer_alembic_revision=writer_alembic_revision,
            source_fingerprint=self.source_fingerprint,
            created_at=created_at,
            runs=self.runs,
            steps=self.steps,
            snapshots=self.snapshots,
            step_configurations=self.step_configurations,
        )


@dataclass(frozen=True)
class _FamilyRows:
    runs: List[PipelineRunSchema]
    steps: List[StepRunSchema]
    snapshots: List[PipelineSnapshotSchema]
    configurations: List[StepConfigurationSchema]


class ExecutionArchiveCapturer:
    """Inspect and capture execution trees without unbounded reads."""

    def __init__(
        self,
        engine: Engine,
        *,
        max_source_bytes: int = (
            DEFAULT_ZENML_SERVER_EXECUTION_ARCHIVE_MAX_DECODED_BYTES
        ),
        max_rows: int = DEFAULT_ZENML_SERVER_EXECUTION_ARCHIVE_MAX_ROWS,
    ) -> None:
        """Initialize the capturer.

        Args:
            engine: SQL store engine.
            max_source_bytes: Largest execution-tree payload that may be loaded.
            max_rows: Largest execution-tree row closure that may be loaded.

        Raises:
            ValueError: If either safety limit is not positive.
        """
        if max_source_bytes <= 0 or max_rows <= 0:
            raise ValueError(
                "Execution archive capture limits must be positive."
            )
        self._engine = engine
        self._max_source_bytes = max_source_bytes
        self._max_rows = max_rows

    def inspect(
        self,
        *,
        project_id: UUID,
        root_run_id: UUID,
        session: Optional[Session] = None,
    ) -> ExecutionArchiveFamily:
        """Inspect an execution tree without loading its payload columns.

        Args:
            project_id: Project that must own the execution tree.
            root_run_id: Root run of the execution tree.
            session: Existing transaction, if any.

        Returns:
            Execution-tree identity, size, and safety evidence.
        """
        with self._session(session) as active_session:
            return self._inspect(
                active_session, project_id, root_run_id, lock=False
            )

    def capture(
        self,
        *,
        project_id: UUID,
        root_run_id: UUID,
        session: Optional[Session] = None,
        for_update: bool = False,
    ) -> ExecutionArchiveCapture:
        """Load a bounded, complete execution tree.

        Locking capture is used by authority-changing operations. It locks
        snapshots, runs, steps, and configurations in the same order used by
        writers, then performs a current locking inspection before encoding.

        Args:
            project_id: Project that must own the execution tree.
            root_run_id: Root run of the execution tree.
            session: Existing transaction, if any.
            for_update: Whether to lock the family until transaction end.

        Returns:
            Complete archive source records.
        """
        with self._session(session) as active_session:
            family = self._inspect(
                active_session, project_id, root_run_id, lock=False
            )
            family.require_exportable()
            self._require_bounded(family)
            rows = self._load_rows(active_session, family, lock=for_update)
            if for_update:
                family = self._inspect(
                    active_session, project_id, root_run_id, lock=True
                )
                family.require_exportable()
                self._require_bounded(family)
            self._require_same_rows(family, rows)
            return _encode(family, rows)

    def _session(self, session: Optional[Session]) -> ContextManager[Session]:
        return nullcontext(session) if session else Session(self._engine)

    def _require_bounded(self, family: ExecutionArchiveFamily) -> None:
        if family.source_bytes > self._max_source_bytes:
            raise ExecutionArchiveError(
                f"The execution tree payload ({family.source_bytes} bytes) "
                f"exceeds the {self._max_source_bytes}-byte archive limit."
            )

    def _inspect(
        self,
        session: Session,
        project_id: UUID,
        root_run_id: UUID,
        *,
        lock: bool,
    ) -> ExecutionArchiveFamily:
        runs = _execute_all(
            session,
            [
                sa_select(
                    col(PipelineRunSchema.id),
                    col(PipelineRunSchema.snapshot_id),
                    col(PipelineRunSchema.parent_run_id),
                    col(PipelineRunSchema.root_run_id),
                    col(PipelineRunSchema.status),
                    col(PipelineRunSchema.updated),
                    col(PipelineRunSchema.end_time),
                ).where(predicate)
                for predicate in _family_run_predicates(
                    project_id, root_run_id
                )
            ],
            lock=lock,
            max_rows=self._max_rows,
            family_row_limit=self._max_rows,
        )
        root = next((run for run in runs if run[0] == root_run_id), None)
        if root is None:
            raise ExecutionArchiveError(
                "The requested root run does not exist in this project."
            )
        if root[2] is not None or root[3] is not None:
            raise ExecutionArchiveError(
                "Execution archives require a root run ID."
            )
        run_ids = {run[0] for run in runs}
        remaining_rows = self._max_rows - len(runs)
        steps = _execute_all(
            session,
            [
                select(
                    StepRunSchema.id,
                    StepRunSchema.snapshot_id,
                    StepRunSchema.status,
                    StepRunSchema.updated,
                ).where(
                    and_(
                        col(StepRunSchema.project_id) == project_id,
                        col(StepRunSchema.pipeline_run_id).in_(chunk),
                    )
                )
                for chunk in chunked_ids(run_ids)
            ],
            lock=lock,
            max_rows=remaining_rows,
            family_row_limit=self._max_rows,
        )
        step_ids = {step[0] for step in steps}
        snapshot_ids = {
            value
            for value in [run[1] for run in runs] + [step[1] for step in steps]
            if value is not None
        }
        snapshots = _execute_all(
            session,
            [
                sa_select(
                    col(PipelineSnapshotSchema.id),
                    col(PipelineSnapshotSchema.name),
                    col(PipelineSnapshotSchema.schedule_id),
                    col(PipelineSnapshotSchema.template_id),
                    col(PipelineSnapshotSchema.updated),
                ).where(
                    and_(
                        col(PipelineSnapshotSchema.project_id) == project_id,
                        col(PipelineSnapshotSchema.id).in_(chunk),
                    )
                )
                for chunk in chunked_ids(snapshot_ids)
            ],
            lock=lock,
            max_rows=remaining_rows - len(steps),
            family_row_limit=self._max_rows,
        )
        if {snapshot[0] for snapshot in snapshots} != snapshot_ids:
            raise ExecutionArchiveError(
                "The execution tree has an incomplete snapshot closure."
            )

        configurations = _execute_all(
            session,
            [
                select(
                    StepConfigurationSchema.id,
                    StepConfigurationSchema.snapshot_id,
                    StepConfigurationSchema.step_run_id,
                    StepConfigurationSchema.updated,
                ).where(col(StepConfigurationSchema.snapshot_id).in_(chunk))
                for chunk in chunked_ids(snapshot_ids)
            ]
            + [
                select(
                    StepConfigurationSchema.id,
                    StepConfigurationSchema.snapshot_id,
                    StepConfigurationSchema.step_run_id,
                    StepConfigurationSchema.updated,
                ).where(col(StepConfigurationSchema.step_run_id).in_(chunk))
                for chunk in chunked_ids(step_ids)
            ],
            lock=lock,
            max_rows=(
                self._max_rows - len(runs) - len(steps) - len(snapshots)
            ),
            family_row_limit=self._max_rows,
        )
        configurations = list({row[0]: row for row in configurations}.values())

        blockers: Set[str] = set()
        if not all(run[4] == ExecutionStatus.COMPLETED.value for run in runs):
            blockers.add("not every pipeline run completed successfully")
        if not all(_is_finished(step[2]) for step in steps):
            blockers.add("not every step is in a terminal state")
        if root[6] is None:
            blockers.add("the root run has no completion time")
        if self._snapshots_are_shared(
            session, snapshot_ids, run_ids, step_ids, lock=lock
        ):
            blockers.add("a snapshot is shared outside the execution tree")
        if self._operational_snapshots(session, snapshots, lock=lock):
            blockers.add(
                "a snapshot is still used as an operational definition"
            )
        blockers.update(
            self._active_blockers(session, run_ids, step_ids, lock=lock)
        )

        updated = (
            [run[5] for run in runs]
            + [step[3] for step in steps]
            + [snapshot[4] for snapshot in snapshots]
            + [configuration[3] for configuration in configurations]
        )
        return ExecutionArchiveFamily(
            project_id=project_id,
            root_run_id=root_run_id,
            run_ids=_sorted_ids(run_ids),
            step_run_ids=_sorted_ids(step_ids),
            snapshot_ids=_sorted_ids(snapshot_ids),
            configuration_ids=_sorted_ids(
                {configuration[0] for configuration in configurations}
            ),
            source_bytes=self._source_bytes(
                session, run_ids, step_ids, snapshot_ids
            ),
            latest_mutation=max(updated),
            completed_at=root[6],
            blockers=sorted(blockers),
        )

    @staticmethod
    def _load_rows(
        session: Session, family: ExecutionArchiveFamily, *, lock: bool
    ) -> _FamilyRows:
        def load(table: Any, ids: Sequence[UUID]) -> List[Any]:
            rows: List[Any] = []
            for chunk in chunked_ids(ids):
                statement = select(table).where(col(table.id).in_(chunk))
                if lock:
                    statement = statement.with_for_update()
                rows.extend(session.exec(statement).all())
            return rows

        return _FamilyRows(
            snapshots=load(PipelineSnapshotSchema, family.snapshot_ids),
            runs=load(PipelineRunSchema, family.run_ids),
            steps=load(StepRunSchema, family.step_run_ids),
            configurations=load(
                StepConfigurationSchema, family.configuration_ids
            ),
        )

    @staticmethod
    def _require_same_rows(
        family: ExecutionArchiveFamily, rows: _FamilyRows
    ) -> None:
        if (
            {row.id for row in rows.runs} != set(family.run_ids)
            or {row.id for row in rows.steps} != set(family.step_run_ids)
            or {row.id for row in rows.snapshots} != set(family.snapshot_ids)
            or {row.id for row in rows.configurations}
            != set(family.configuration_ids)
        ):
            raise ExecutionArchiveError(
                "The execution tree changed while it was being captured."
            )

    @staticmethod
    def _source_bytes(
        session: Session,
        run_ids: Set[UUID],
        step_ids: Set[UUID],
        snapshot_ids: Set[UUID],
    ) -> int:
        def total(
            table: Any,
            fields: Sequence[str],
            column: Any,
            ids: Set[UUID],
        ) -> int:
            lengths = [
                func.coalesce(func.length(getattr(table, field)), 0)
                for field in fields
            ]
            expression = sum(lengths[1:], lengths[0])
            return sum(
                int(
                    session.exec(
                        select(func.coalesce(func.sum(expression), 0)).where(
                            col(column).in_(chunk)
                        )
                    ).one()
                )
                for chunk in chunked_ids(ids)
            )

        return (
            total(
                PipelineRunSchema,
                ARCHIVED_RUN_FIELDS,
                PipelineRunSchema.id,
                run_ids,
            )
            + total(
                StepRunSchema,
                ARCHIVED_STEP_FIELDS,
                StepRunSchema.id,
                step_ids,
            )
            + total(
                PipelineSnapshotSchema,
                ARCHIVED_SNAPSHOT_FIELDS,
                PipelineSnapshotSchema.id,
                snapshot_ids,
            )
            + total(
                StepConfigurationSchema,
                ARCHIVED_CONFIGURATION_FIELDS,
                StepConfigurationSchema.snapshot_id,
                snapshot_ids,
            )
            + total(
                StepConfigurationSchema,
                ARCHIVED_CONFIGURATION_FIELDS,
                StepConfigurationSchema.step_run_id,
                step_ids,
            )
        )

    @staticmethod
    def _snapshots_are_shared(
        session: Session,
        snapshot_ids: Set[UUID],
        run_ids: Set[UUID],
        step_ids: Set[UUID],
        *,
        lock: bool,
    ) -> bool:
        for id_column, snapshot_column, family_ids in (
            (
                PipelineRunSchema.id,
                PipelineRunSchema.snapshot_id,
                run_ids,
            ),
            (StepRunSchema.id, StepRunSchema.snapshot_id, step_ids),
        ):
            for chunk in chunked_ids(snapshot_ids):
                statement = select(id_column).where(
                    col(snapshot_column).in_(chunk)
                )
                if family_ids:
                    statement = statement.where(
                        col(id_column).not_in(family_ids)
                    )
                if _execute_all(session, [statement.limit(1)], lock=lock):
                    return True
        return False

    @staticmethod
    def _operational_snapshots(
        session: Session, snapshots: Sequence[Any], *, lock: bool
    ) -> Set[UUID]:
        snapshot_ids = {snapshot[0] for snapshot in snapshots}
        operational = {
            snapshot[0]
            for snapshot in snapshots
            if any(snapshot[index] is not None for index in (1, 2, 3))
        }
        for column in (
            DeploymentSchema.snapshot_id,
            RunTemplateSchema.source_snapshot_id,
            TriggerSnapshotSchema.snapshot_id,
            PipelineSnapshotSchema.source_snapshot_id,
        ):
            operational.update(
                row[0]
                for row in _execute_all(
                    session,
                    [
                        select(column).where(col(column).in_(chunk))
                        for chunk in chunked_ids(snapshot_ids)
                    ],
                    lock=lock,
                )
                if row[0] is not None
            )
        return operational

    @staticmethod
    def _active_blockers(
        session: Session,
        run_ids: Set[UUID],
        step_ids: Set[UUID],
        *,
        lock: bool,
    ) -> Set[str]:
        finished = [
            status.value for status in ExecutionStatus if status.is_finished
        ]
        inactive = [
            ServiceState.INACTIVE.value,
            ServiceState.SCALED_TO_ZERO.value,
        ]
        checks = {
            "a run still has a pending wait condition": (
                RunWaitConditionSchema.run_id,
                run_ids,
                col(RunWaitConditionSchema.status)
                == RunWaitConditionStatus.PENDING.value,
            ),
            "a hook invocation is unfinished": (
                HookInvocationSchema.pipeline_run_id,
                run_ids,
                col(HookInvocationSchema.status).not_in(finished),
            ),
            "a run still owns an active service": (
                ServiceSchema.pipeline_run_id,
                run_ids,
                or_(
                    col(ServiceSchema.state).is_(None),
                    col(ServiceSchema.state).not_in(inactive),
                ),
            ),
            "a step still owns an active resource request": (
                ResourceRequestSchema.step_run_id,
                step_ids,
                col(ResourceRequestSchema.status).in_(
                    [
                        ResourceRequestStatus.PENDING.value,
                        ResourceRequestStatus.ALLOCATED.value,
                        ResourceRequestStatus.PREEMPTING.value,
                    ]
                ),
            ),
        }
        blockers: Set[str] = set()
        for blocker, (column, ids, predicate) in checks.items():
            if any(
                _execute_all(
                    session,
                    [
                        select(column)
                        .where(col(column).in_(chunk))
                        .where(predicate)
                        .limit(1)
                    ],
                    lock=lock,
                )
                for chunk in chunked_ids(ids)
            ):
                blockers.add(blocker)
        return blockers


def _encode(
    family: ExecutionArchiveFamily, rows: _FamilyRows
) -> ExecutionArchiveCapture:
    runs = [_run_payload(row) for row in _sorted_rows(rows.runs)]
    steps = [_step_payload(row) for row in _sorted_rows(rows.steps)]
    snapshots = [
        _snapshot_payload(row) for row in _sorted_rows(rows.snapshots)
    ]
    configurations = [
        _configuration_payload(row)
        for row in _sorted_rows(rows.configurations)
    ]
    return ExecutionArchiveCapture(
        family=family,
        runs=runs,
        steps=steps,
        snapshots=snapshots,
        step_configurations=configurations,
        source_fingerprint=execution_archive_source_fingerprint(
            runs=runs,
            steps=steps,
            snapshots=snapshots,
            step_configurations=configurations,
        ),
    )


def _run_payload(row: PipelineRunSchema) -> ArchivedPipelineRunPayload:
    require_active_payload(
        *(getattr(row, field) for field in ARCHIVED_RUN_FIELDS)
    )
    return ArchivedPipelineRunPayload(
        id=row.id,
        orchestrator_environment=row.orchestrator_environment,
        exception_info=row.exception_info,
        pipeline_configuration=row.pipeline_configuration,
        client_environment=row.client_environment,
    )


def _step_payload(row: StepRunSchema) -> ArchivedStepRunPayload:
    require_active_payload(
        *(getattr(row, field) for field in ARCHIVED_STEP_FIELDS)
    )
    return ArchivedStepRunPayload(
        id=row.id,
        source_code=row.source_code,
        docstring=row.docstring,
        exception_info=row.exception_info,
        step_configuration=row.step_configuration,
    )


def _snapshot_payload(
    row: PipelineSnapshotSchema,
) -> ArchivedPipelineSnapshotPayload:
    require_active_payload(
        *(getattr(row, field) for field in ARCHIVED_SNAPSHOT_FIELDS)
    )
    return ArchivedPipelineSnapshotPayload(
        id=row.id,
        pipeline_configuration=row.pipeline_configuration,
        client_environment=row.client_environment,
        pipeline_spec=row.pipeline_spec,
        source_code=row.source_code,
    )


def _configuration_payload(
    row: StepConfigurationSchema,
) -> ArchivedStepConfigurationPayload:
    require_active_payload(row.config)
    return ArchivedStepConfigurationPayload(
        id=row.id,
        snapshot_id=row.snapshot_id,
        step_run_id=row.step_run_id,
        index=row.index,
        name=row.name,
        config=row.config,
    )


def _family_run_predicates(project_id: UUID, root_run_id: UUID) -> List[Any]:
    return [
        and_(
            col(PipelineRunSchema.project_id) == project_id,
            col(PipelineRunSchema.id) == root_run_id,
        ),
        and_(
            col(PipelineRunSchema.project_id) == project_id,
            col(PipelineRunSchema.root_run_id) == root_run_id,
        ),
    ]


def _execute_all(
    session: Session,
    statements: Iterable[Any],
    *,
    lock: bool,
    max_rows: Optional[int] = None,
    family_row_limit: Optional[int] = None,
) -> List[Any]:
    rows: List[Any] = []
    for statement in statements:
        if max_rows is not None:
            statement = statement.limit(max_rows - len(rows) + 1)
        if lock:
            statement = statement.with_for_update(read=True)
        rows.extend(session.execute(statement).all())
        if max_rows is not None and len(rows) > max_rows:
            raise ExecutionArchiveNotEligibleError(
                "The execution tree exceeds the "
                f"{family_row_limit or max_rows}-row archive limit."
            )
    return rows


def chunked_ids(values: Iterable[UUID]) -> List[List[UUID]]:
    """Return stable, deduplicated ID chunks for bounded SQL predicates.

    Args:
        values: IDs to sort, deduplicate, and partition.

    Returns:
        Stable chunks containing at most 500 IDs each.
    """
    ordered = sorted(set(values), key=lambda value: value.hex)
    return [
        ordered[index : index + _ID_CHUNK_SIZE]
        for index in range(0, len(ordered), _ID_CHUNK_SIZE)
    ]


def _sorted_ids(values: Iterable[UUID]) -> List[UUID]:
    return sorted(set(values), key=lambda value: value.hex)


def _sorted_rows(values: Sequence[Any]) -> List[Any]:
    return sorted(values, key=lambda value: value.id.hex)


def _is_finished(value: str) -> bool:
    try:
        return ExecutionStatus(value).is_finished
    except ValueError:
        return False
