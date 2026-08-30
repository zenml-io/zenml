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
"""Capture of one execution family from SQL.

A family is inspected first: identities, status, sizes and closure are read
without loading any payload, so a preview costs no payload read and a family
too large to archive is refused before its payload is ever held in memory.
The payload is then loaded once, encoded once, and kept only in its
compressed form together with the digests that identify it.
"""

from contextlib import nullcontext
from datetime import datetime
from typing import (
    Any,
    ContextManager,
    Dict,
    List,
    Optional,
    Sequence,
    Set,
    Type,
    TypeVar,
)
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from sqlalchemy import func
from sqlalchemy import select as sa_select
from sqlalchemy.engine import Engine
from sqlmodel import Session, and_, col, or_, select

from zenml.constants import (
    DEFAULT_ZENML_SERVER_EXECUTION_ARCHIVE_MAX_FAMILY_STORED_BYTES,
)
from zenml.enums import (
    ExecutionStatus,
    ResourceRequestStatus,
    RunWaitConditionStatus,
    ServiceState,
)
from zenml.models import ExecutionArchiveObject
from zenml.zen_stores.execution_archive.codec import (
    canonical_json,
    compress,
    sha256_digest,
)
from zenml.zen_stores.execution_archive.exceptions import (
    ExecutionArchiveError,
)
from zenml.zen_stores.execution_archive.payload import (
    ARCHIVED_CONFIGURATION_FIELDS,
    ARCHIVED_PAYLOAD_PLACEHOLDER,
    ARCHIVED_RUN_FIELDS,
    ARCHIVED_SNAPSHOT_FIELDS,
    ARCHIVED_STEP_FIELDS,
    ArchivedPipelineRunPayload,
    ArchivedPipelineSnapshotPayload,
    ArchivedStepConfigurationPayload,
    ArchivedStepRunPayload,
    ExecutionPayload,
    SnapshotPayload,
)
from zenml.zen_stores.execution_archive.utils import batched
from zenml.zen_stores.schemas import (
    BaseSchema,
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

S = TypeVar("S", bound=BaseSchema)
Statement = TypeVar("Statement", bound=Any)
# `IN` lists are chunked so a family with many steps never produces a
# statement larger than the database accepts.
_ID_CHUNK = 1000


class ExecutionArchiveFamily(BaseModel):
    """The rows and closure evidence of one family, without its payload."""

    project_id: UUID
    root_run_id: UUID
    run_ids: List[UUID]
    step_run_ids: List[UUID]
    snapshot_ids: List[UUID]
    static_configuration_ids: List[UUID]
    dynamic_configuration_ids: List[UUID]
    stored_bytes: int
    latest_mutation: datetime
    completed: bool
    operational_snapshot_ids: List[UUID]
    active_blockers: List[str]

    model_config = ConfigDict(frozen=True)

    @property
    def table_counts(self) -> Dict[str, int]:
        """The number of rows the family has in every archived table.

        Returns:
            The counts keyed by table name.
        """
        return {
            "pipeline_run": len(self.run_ids),
            "step_run": len(self.step_run_ids),
            "pipeline_snapshot": len(self.snapshot_ids),
            "step_configuration": len(self.static_configuration_ids)
            + len(self.dynamic_configuration_ids),
        }


class ExecutionArchiveCapture(BaseModel):
    """A family with its payload, compressed as the archive stores it."""

    family: ExecutionArchiveFamily
    execution_compressed: bytes
    execution_object: ExecutionArchiveObject
    snapshot_compressed: bytes
    snapshot_object: ExecutionArchiveObject
    # What "the family did not change" means: the digests of both payload
    # objects, which cover every archived column of every archived row.
    source_fingerprint: str

    model_config = ConfigDict(frozen=True)


class _FamilyRows(BaseModel):
    """The payload rows of a family, loaded once."""

    snapshots: List[PipelineSnapshotSchema]
    runs: List[PipelineRunSchema]
    steps: List[StepRunSchema]
    configurations: List[StepConfigurationSchema]

    model_config = ConfigDict(arbitrary_types_allowed=True)


class ExecutionArchiveCapturer:
    """Reads execution families from SQL."""

    def __init__(
        self,
        engine: Engine,
        *,
        max_stored_bytes: int = (
            DEFAULT_ZENML_SERVER_EXECUTION_ARCHIVE_MAX_FAMILY_STORED_BYTES
        ),
    ) -> None:
        """Initialize the capturer.

        Args:
            engine: The SQL store engine.
            max_stored_bytes: The largest payload a capture may load.
        """
        self._engine = engine
        self._max_stored_bytes = max_stored_bytes

    def inspect(
        self,
        *,
        project_id: UUID,
        root_run_id: UUID,
        session: Optional[Session] = None,
    ) -> ExecutionArchiveFamily:
        """Read a family's identities and closure without its payload.

        Args:
            project_id: The project owning the family.
            root_run_id: The root run of the family.
            session: An existing transaction to read in.

        Returns:
            The family.
        """
        with self._session(session) as session:
            return self._inspect(session, project_id, root_run_id, False)

    def capture(
        self,
        *,
        project_id: UUID,
        root_run_id: UUID,
        session: Optional[Session] = None,
        for_update: bool = False,
    ) -> ExecutionArchiveCapture:
        """Read one family with its payload.

        Args:
            project_id: The project owning the family.
            root_run_id: The root run of the family.
            session: An existing transaction to read in.
            for_update: Whether to lock every payload row for the rest of
                the transaction. Rows are locked in the order snapshot,
                run, step, configuration, the order `create_run_step` uses,
                so archive workers and writers cannot deadlock. The closure
                is then inspected again with locking reads: under
                REPEATABLE READ a plain read would not see a writer that
                committed while this transaction waited for its locks.

        Returns:
            The captured family.

        Raises:
            ExecutionArchiveError: If the run is not a root run of the
                project, the family is not closed, or its payload is too
                large to archive.
        """
        with self._session(session) as session:
            if for_update:
                preliminary = self._inspect(
                    session, project_id, root_run_id, False
                )
                rows = self._load_rows(session, preliminary, lock=True)
                family = self._inspect(session, project_id, root_run_id, True)
            else:
                family = self._inspect(session, project_id, root_run_id, False)
                if family.stored_bytes > self._max_stored_bytes:
                    raise ExecutionArchiveError(
                        f"The execution family payload ({family.stored_bytes}"
                        " stored bytes) is too large to archive."
                    )
                rows = self._load_rows(session, family, lock=False)
            if (
                {row.id for row in rows.runs} != set(family.run_ids)
                or {row.id for row in rows.steps} != set(family.step_run_ids)
                or {row.id for row in rows.snapshots}
                != set(family.snapshot_ids)
                or {row.id for row in rows.configurations}
                != set(family.static_configuration_ids)
                | set(family.dynamic_configuration_ids)
            ):
                raise ExecutionArchiveError(
                    "The execution family changed while it was being read."
                )
            return _encode(family, rows)

    def _session(self, session: Optional[Session]) -> ContextManager[Session]:
        return nullcontext(session) if session else Session(self._engine)

    def _inspect(
        self,
        session: Session,
        project_id: UUID,
        root_run_id: UUID,
        for_update: bool,
    ) -> ExecutionArchiveFamily:
        """Read identities, status and closure with id-only queries.

        Args:
            session: The SQL session.
            project_id: The project owning the family.
            root_run_id: The root run of the family.
            for_update: Whether the family's rows are locked and every
                read must see the latest committed rows.

        Returns:
            The family.

        Raises:
            ExecutionArchiveError: If the run is not a root run of the
                project or the family's snapshots are shared or missing.
        """
        runs = _all(
            session,
            [
                sa_select(
                    col(PipelineRunSchema.id),
                    col(PipelineRunSchema.snapshot_id),
                    col(PipelineRunSchema.parent_run_id),
                    col(PipelineRunSchema.root_run_id),
                    col(PipelineRunSchema.status),
                    col(PipelineRunSchema.updated),
                ).where(predicate)
                for predicate in _family_run_predicates(
                    project_id, root_run_id
                )
            ],
            for_update,
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
        steps = _all(
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
                for chunk in batched(run_ids, _ID_CHUNK)
            ],
            for_update,
        )
        step_ids = {step[0] for step in steps}
        snapshot_ids = {
            snapshot_id
            for snapshot_id in [run[1] for run in runs]
            + [step[1] for step in steps]
            if snapshot_id is not None
        }
        snapshots = _all(
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
                for chunk in batched(snapshot_ids, _ID_CHUNK)
            ],
            for_update,
        )
        if {snapshot[0] for snapshot in snapshots} != snapshot_ids:
            raise ExecutionArchiveError(
                "The execution family has an incomplete snapshot closure."
            )
        configurations = _all(
            session,
            [
                select(
                    StepConfigurationSchema.id,
                    StepConfigurationSchema.snapshot_id,
                    StepConfigurationSchema.updated,
                ).where(col(StepConfigurationSchema.snapshot_id).in_(chunk))
                for chunk in batched(snapshot_ids, _ID_CHUNK)
            ]
            + [
                select(
                    StepConfigurationSchema.id,
                    StepConfigurationSchema.snapshot_id,
                    StepConfigurationSchema.updated,
                ).where(col(StepConfigurationSchema.step_run_id).in_(chunk))
                for chunk in batched(step_ids, _ID_CHUNK)
            ],
            for_update,
        )
        self._assert_exclusive_snapshots(
            session, snapshot_ids, run_ids, step_ids, for_update
        )
        updated = (
            [run[5] for run in runs]
            + [step[3] for step in steps]
            + [snapshot[4] for snapshot in snapshots]
            + [configuration[2] for configuration in configurations]
        )
        operational = {
            snapshot[0]
            for snapshot in snapshots
            if snapshot[1] is not None
            or snapshot[2] is not None
            or snapshot[3] is not None
        } | self._referenced_snapshot_ids(session, snapshot_ids, for_update)
        return ExecutionArchiveFamily(
            project_id=project_id,
            root_run_id=root_run_id,
            run_ids=_sorted(run_ids),
            step_run_ids=_sorted(step_ids),
            snapshot_ids=_sorted(snapshot_ids),
            static_configuration_ids=_sorted(
                {c[0] for c in configurations if c[1] is not None}
            ),
            dynamic_configuration_ids=_sorted(
                {c[0] for c in configurations if c[1] is None}
            ),
            stored_bytes=self._stored_payload_bytes(
                session, run_ids, step_ids, snapshot_ids
            ),
            latest_mutation=max(updated),
            completed=all(
                run[4] == ExecutionStatus.COMPLETED.value for run in runs
            )
            and all(ExecutionStatus(step[2]).is_finished for step in steps),
            operational_snapshot_ids=_sorted(operational),
            active_blockers=sorted(
                self._active_blockers(session, run_ids, step_ids, for_update)
            ),
        )

    @staticmethod
    def _load_rows(
        session: Session, family: ExecutionArchiveFamily, *, lock: bool
    ) -> _FamilyRows:
        """Load the payload rows of a family, in the writers' lock order.

        Args:
            session: The SQL session.
            family: The family whose rows to load.
            lock: Whether to lock the rows for the transaction.

        Returns:
            The rows.
        """

        def load(table: Type[S], ids: Sequence[UUID]) -> List[S]:
            rows: List[S] = []
            for chunk in batched(ids, _ID_CHUNK):
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
                StepConfigurationSchema,
                family.static_configuration_ids
                + family.dynamic_configuration_ids,
            ),
        )

    @staticmethod
    def _stored_payload_bytes(
        session: Session,
        run_ids: Set[UUID],
        step_ids: Set[UUID],
        snapshot_ids: Set[UUID],
    ) -> int:
        """Sum the byte length of every payload column of a family.

        A conservative bound on the JSON the family holds, computed in SQL
        before any payload is loaded.

        Args:
            session: The SQL session.
            run_ids: The runs of the family.
            step_ids: The step runs of the family.
            snapshot_ids: The snapshots of the family.

        Returns:
            The bytes the family's payload columns hold.
        """

        def total(
            table: Type[BaseSchema],
            fields: Sequence[str],
            column: Any,
            ids: Set[UUID],
        ) -> int:
            lengths = [
                func.coalesce(func.length(getattr(table, field)), 0)
                for field in fields
            ]
            return sum(
                int(
                    session.exec(
                        select(
                            func.coalesce(
                                func.sum(sum(lengths[1:], lengths[0])), 0
                            )
                        ).where(col(column).in_(chunk))
                    ).one()
                )
                for chunk in batched(ids, _ID_CHUNK)
            )

        return (
            total(
                PipelineRunSchema,
                ARCHIVED_RUN_FIELDS,
                PipelineRunSchema.id,
                run_ids,
            )
            + total(
                StepRunSchema, ARCHIVED_STEP_FIELDS, StepRunSchema.id, step_ids
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
    def _assert_exclusive_snapshots(
        session: Session,
        snapshot_ids: Set[UUID],
        run_ids: Set[UUID],
        step_ids: Set[UUID],
        for_update: bool,
    ) -> None:
        """Reject snapshots that runs or steps outside the family use.

        Compacting a shared snapshot would leave the outside entity without
        payload and without an archive to hydrate it from.

        Args:
            session: The SQL session.
            snapshot_ids: The snapshots of the family.
            run_ids: The runs of the family.
            step_ids: The step runs of the family.
            for_update: Whether to read the latest committed rows.

        Raises:
            ExecutionArchiveError: If an outside run or step shares one.
        """
        for chunk in batched(snapshot_ids, _ID_CHUNK):
            shared = _all(
                session,
                [
                    select(PipelineRunSchema.id)
                    .where(col(PipelineRunSchema.snapshot_id).in_(chunk))
                    .where(col(PipelineRunSchema.id).not_in(run_ids))
                    .limit(1),
                    select(StepRunSchema.id)
                    .where(col(StepRunSchema.snapshot_id).in_(chunk))
                    .where(col(StepRunSchema.id).not_in(step_ids))
                    .limit(1),
                ],
                for_update,
            )
            if shared:
                raise ExecutionArchiveError(
                    "Execution archives require snapshots that no run or "
                    "step outside the family uses."
                )

    @staticmethod
    def _referenced_snapshot_ids(
        session: Session, snapshot_ids: Set[UUID], for_update: bool
    ) -> Set[UUID]:
        """Snapshots that an operational entity references.

        Args:
            session: The SQL session.
            snapshot_ids: The snapshots of the family.
            for_update: Whether to read the latest committed rows.

        Returns:
            The referenced snapshot IDs.
        """
        referenced: Set[UUID] = set()
        for column in (
            DeploymentSchema.snapshot_id,
            RunTemplateSchema.source_snapshot_id,
            TriggerSnapshotSchema.snapshot_id,
            PipelineSnapshotSchema.source_snapshot_id,
        ):
            referenced.update(
                row[0]
                for row in _all(
                    session,
                    [
                        select(column).where(col(column).in_(chunk))
                        for chunk in batched(snapshot_ids, _ID_CHUNK)
                    ],
                    for_update,
                )
                if row[0] is not None
            )
        return referenced

    @staticmethod
    def _active_blockers(
        session: Session,
        run_ids: Set[UUID],
        step_ids: Set[UUID],
        for_update: bool,
    ) -> Set[str]:
        """Runtime state that makes archiving unsafe right now.

        Args:
            session: The SQL session.
            run_ids: The runs of the family.
            step_ids: The step runs of the family.
            for_update: Whether to read the latest committed rows.

        Returns:
            Human-readable blockers.
        """
        finished = [
            status.value for status in ExecutionStatus if status.is_finished
        ]
        inactive = [
            ServiceState.INACTIVE.value,
            ServiceState.SCALED_TO_ZERO.value,
        ]
        checks = {
            "pending wait condition": select(RunWaitConditionSchema.id)
            .where(col(RunWaitConditionSchema.run_id).in_(run_ids))
            .where(
                col(RunWaitConditionSchema.status)
                == RunWaitConditionStatus.PENDING.value
            ),
            "unfinished hook invocation": select(HookInvocationSchema.id)
            .where(col(HookInvocationSchema.pipeline_run_id).in_(run_ids))
            .where(col(HookInvocationSchema.status).not_in(finished)),
            "active service": select(ServiceSchema.id)
            .where(col(ServiceSchema.pipeline_run_id).in_(run_ids))
            .where(
                or_(
                    col(ServiceSchema.state).is_(None),
                    col(ServiceSchema.state).not_in(inactive),
                )
            ),
            "active resource request": select(ResourceRequestSchema.id)
            .where(col(ResourceRequestSchema.step_run_id).in_(step_ids))
            .where(
                col(ResourceRequestSchema.status).in_(
                    [
                        ResourceRequestStatus.PENDING.value,
                        ResourceRequestStatus.ALLOCATED.value,
                        ResourceRequestStatus.PREEMPTING.value,
                    ]
                )
            ),
        }
        return {
            blocker
            for blocker, statement in checks.items()
            if _all(session, [statement.limit(1)], for_update)
        }


def _family_run_predicates(project_id: UUID, root_run_id: UUID) -> List[Any]:
    """The `pipeline_run` rows of a family, as two indexed predicates.

    The root is found by primary key and the nested runs by `root_run_id`;
    a single `OR` predicate could make a locking read scan the project.

    Args:
        project_id: The project owning the family.
        root_run_id: The root run of the family.

    Returns:
        The SQL predicates.
    """
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


def _all(
    session: Session, statements: Sequence[Statement], for_update: bool
) -> List[Any]:
    """Run several statements and concatenate their rows.

    Args:
        session: The SQL session.
        statements: The statements.
        for_update: Whether to read the latest committed rows with a
            shared lock, which is what the capture needs while it holds
            row locks: the rows must not change until the transaction
            ends, and reading them must see what others committed.

    Returns:
        The rows of every statement.
    """
    rows: List[Any] = []
    for statement in statements:
        if for_update:
            statement = statement.with_for_update(read=True)
        rows.extend(session.execute(statement).all())
    return rows


def _sorted(ids: Set[UUID]) -> List[UUID]:
    return sorted(ids, key=lambda value: value.hex)


def _by_id(rows: Sequence[S]) -> List[S]:
    return sorted(rows, key=lambda row: row.id.hex)


def _encode(
    family: ExecutionArchiveFamily, rows: _FamilyRows
) -> ExecutionArchiveCapture:
    """Encode and compress a family's payload once.

    Args:
        family: The family.
        rows: Its payload rows.

    Returns:
        The capture.
    """
    execution = canonical_json(
        ExecutionPayload(
            root_run_id=family.root_run_id,
            runs=[_run_payload(run) for run in _by_id(rows.runs)],
            steps=[_step_payload(step) for step in _by_id(rows.steps)],
            step_configurations=[
                _configuration_payload(configuration)
                for configuration in _by_id(rows.configurations)
                if configuration.snapshot_id is None
            ],
        )
    )
    snapshots = canonical_json(
        SnapshotPayload(
            snapshots=[
                _snapshot_payload(snapshot)
                for snapshot in _by_id(rows.snapshots)
            ],
            step_configurations=[
                _configuration_payload(configuration)
                for configuration in _by_id(rows.configurations)
                if configuration.snapshot_id is not None
            ],
        )
    )
    execution_compressed, snapshots_compressed = (
        compress(execution),
        compress(snapshots),
    )
    execution_object = _object(execution_compressed)
    snapshot_object = _object(snapshots_compressed)
    return ExecutionArchiveCapture(
        family=family,
        execution_compressed=execution_compressed,
        execution_object=execution_object,
        snapshot_compressed=snapshots_compressed,
        snapshot_object=snapshot_object,
        source_fingerprint=sha256_digest(
            (execution_object.sha256 + snapshot_object.sha256).encode()
        ),
    )


def _object(compressed: bytes) -> ExecutionArchiveObject:
    return ExecutionArchiveObject(
        sha256=sha256_digest(compressed), stored_bytes=len(compressed)
    )


def _require_hot(row: BaseSchema, fields: Sequence[str]) -> None:
    if any(
        getattr(row, field) == ARCHIVED_PAYLOAD_PLACEHOLDER for field in fields
    ):
        raise ExecutionArchiveError(
            f"{type(row).__name__} {row.id} holds archived payload; the "
            "family is already archived."
        )


def _run_payload(run: PipelineRunSchema) -> ArchivedPipelineRunPayload:
    _require_hot(run, ARCHIVED_RUN_FIELDS)
    return ArchivedPipelineRunPayload(
        id=run.id,
        orchestrator_environment=run.orchestrator_environment,
        exception_info=run.exception_info,
        pipeline_configuration=run.pipeline_configuration,
        client_environment=run.client_environment,
    )


def _step_payload(step: StepRunSchema) -> ArchivedStepRunPayload:
    _require_hot(step, ARCHIVED_STEP_FIELDS)
    return ArchivedStepRunPayload(
        id=step.id,
        source_code=step.source_code,
        docstring=step.docstring,
        exception_info=step.exception_info,
        step_configuration=step.step_configuration,
    )


def _snapshot_payload(
    snapshot: PipelineSnapshotSchema,
) -> ArchivedPipelineSnapshotPayload:
    _require_hot(snapshot, ARCHIVED_SNAPSHOT_FIELDS)
    return ArchivedPipelineSnapshotPayload(
        id=snapshot.id,
        pipeline_configuration=snapshot.pipeline_configuration,
        client_environment=snapshot.client_environment,
        pipeline_spec=snapshot.pipeline_spec,
        source_code=snapshot.source_code,
    )


def _configuration_payload(
    configuration: StepConfigurationSchema,
) -> ArchivedStepConfigurationPayload:
    _require_hot(configuration, ARCHIVED_CONFIGURATION_FIELDS)
    return ArchivedStepConfigurationPayload(
        id=configuration.id,
        snapshot_id=configuration.snapshot_id,
        step_run_id=configuration.step_run_id,
        index=configuration.index,
        name=configuration.name,
        config=configuration.config,
    )
