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
"""Hydration of archived payload onto loaded SQL rows.

Rows are hydrated in batches right after they are loaded and before they
are converted to response models, so conversion itself never touches the
archive. Only rows that hold the archive placeholder in a payload column
need anything: a batch without one costs no query and no object read, a
value written after the archive was taken stays in SQL and wins, and a row
the archive does not cover keeps the payload SQL holds for it.
"""

from typing import (
    Callable,
    Dict,
    Optional,
    Sequence,
    Set,
    Tuple,
    Union,
    cast,
)
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from sqlmodel import Session, col, select

from zenml.constants import DEFAULT_ZENML_SERVER_EXECUTION_ARCHIVE_CACHE_BYTES
from zenml.exceptions import ArchiveUnavailableError
from zenml.models import ExecutionArchiveObject, ExecutionArchiveResponse
from zenml.zen_stores.execution_archive.cache import ExecutionArchiveCache
from zenml.zen_stores.execution_archive.catalog import ExecutionArchiveCatalog
from zenml.zen_stores.execution_archive.models import ArchiveObjectKind
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
from zenml.zen_stores.execution_archive.targets import ExecutionArchiveTargets
from zenml.zen_stores.execution_archive.utils import (
    has_absent_fields,
    is_loaded,
    overlay_absent_fields,
)
from zenml.zen_stores.schemas.pipeline_run_schemas import PipelineRunSchema
from zenml.zen_stores.schemas.pipeline_snapshot_schemas import (
    PipelineSnapshotSchema,
    StepConfigurationSchema,
)
from zenml.zen_stores.schemas.step_run_schemas import StepRunSchema

# Decoded Pydantic objects take several times the memory of their JSON form;
# weighing entries at four times the decompressed length keeps the budget
# honest without serializing the object again.
_DECODED_WEIGHT_FACTOR = 4


class DecodedExecution(BaseModel):
    """An execution payload indexed by row ID."""

    runs: Dict[UUID, ArchivedPipelineRunPayload]
    steps: Dict[UUID, ArchivedStepRunPayload]
    configurations: Dict[UUID, ArchivedStepConfigurationPayload]

    model_config = ConfigDict(frozen=True)

    @classmethod
    def from_payload(cls, payload: ExecutionPayload) -> "DecodedExecution":
        """Index a payload.

        Args:
            payload: The execution payload.

        Returns:
            The indexed payload.
        """
        return cls(
            runs={run.id: run for run in payload.runs},
            steps={step.id: step for step in payload.steps},
            configurations={c.id: c for c in payload.step_configurations},
        )


class DecodedSnapshots(BaseModel):
    """A snapshot payload indexed by row ID."""

    snapshots: Dict[UUID, ArchivedPipelineSnapshotPayload]
    configurations: Dict[UUID, ArchivedStepConfigurationPayload]

    model_config = ConfigDict(frozen=True)

    @classmethod
    def from_payload(cls, payload: SnapshotPayload) -> "DecodedSnapshots":
        """Index a payload.

        Args:
            payload: The snapshot payload.

        Returns:
            The indexed payload.
        """
        return cls(
            snapshots={
                snapshot.id: snapshot for snapshot in payload.snapshots
            },
            configurations={c.id: c for c in payload.step_configurations},
        )


Decoded = Union[DecodedExecution, DecodedSnapshots]


class ExecutionArchiveHydrator:
    """Fills archived payload into loaded run, step and snapshot rows."""

    def __init__(
        self,
        targets: ExecutionArchiveTargets,
        *,
        cache_bytes: int = DEFAULT_ZENML_SERVER_EXECUTION_ARCHIVE_CACHE_BYTES,
    ) -> None:
        """Initialize the hydrator.

        Args:
            targets: Opens the object store of every readable target.
            cache_bytes: Budget of the cache of decoded payload objects.
        """
        self._targets = targets
        self._cache: ExecutionArchiveCache[Decoded] = ExecutionArchiveCache(
            cache_bytes
        )

    def hydrate_runs(
        self, session: Session, runs: Sequence[PipelineRunSchema]
    ) -> None:
        """Hydrate runs and their loaded snapshots.

        Args:
            session: The session the rows were loaded in.
            runs: The runs.
        """
        self._hydrate(
            session,
            runs=list(runs),
            snapshots=[
                run.snapshot
                for run in runs
                if is_loaded(run, "snapshot") and run.snapshot is not None
            ],
        )

    def hydrate_steps(
        self, session: Session, steps: Sequence[StepRunSchema]
    ) -> None:
        """Hydrate step runs, their configurations and loaded snapshots.

        Args:
            session: The session the rows were loaded in.
            steps: The step runs.
        """
        self._hydrate(
            session,
            steps=list(steps),
            snapshots=[
                step.snapshot
                for step in steps
                if is_loaded(step, "snapshot") and step.snapshot is not None
            ],
        )

    def hydrate_snapshots(
        self, session: Session, snapshots: Sequence[PipelineSnapshotSchema]
    ) -> None:
        """Hydrate snapshots and their step configurations.

        Args:
            session: The session the rows were loaded in.
            snapshots: The snapshots.
        """
        self._hydrate(
            session, snapshots=list(snapshots), load_configurations=True
        )

    def hydrate_family(self, session: Session, run: PipelineRunSchema) -> None:
        """Hydrate a run with whatever of its family is already loaded.

        Relationships the query did not load are left alone; loading every
        step run of a run only to scan it would cost more than any
        hydration saves.

        Args:
            session: The session the rows were loaded in.
            run: The run.
        """
        self._hydrate(
            session,
            runs=[run],
            steps=list(run.step_runs) if is_loaded(run, "step_runs") else [],
            snapshots=[run.snapshot]
            if is_loaded(run, "snapshot") and run.snapshot is not None
            else [],
        )

    def _hydrate(
        self,
        session: Session,
        *,
        runs: Sequence[PipelineRunSchema] = (),
        steps: Sequence[StepRunSchema] = (),
        snapshots: Sequence[PipelineSnapshotSchema] = (),
        load_configurations: bool = False,
    ) -> None:
        """Hydrate the rows that hold archived payload.

        Args:
            session: The session the rows were loaded in.
            runs: The runs.
            steps: The step runs.
            snapshots: The snapshots.
            load_configurations: Whether the snapshots are read for their
                step configurations, which are then loaded and hydrated
                even if the query did not load them.
        """
        runs = [run for run in runs if _run_needs_payload(run)]
        steps = [step for step in steps if _step_needs_payload(step)]
        snapshots = [
            snapshot
            for snapshot in snapshots
            if _snapshot_needs_payload(snapshot, load_configurations)
        ]
        if not runs and not steps and not snapshots:
            return

        roots = _family_roots(session, runs, steps)
        archives_by_id = {
            archive.id: archive
            for archive in ExecutionArchiveCatalog.authoritative(
                session, root_run_ids=set(roots.values())
            )
        }
        archives = {
            archive.root_run_id: archive for archive in archives_by_id.values()
        }
        archives_by_id.update(
            (archive.id, archive)
            for archive in ExecutionArchiveCatalog.authoritative(
                session,
                archive_ids={
                    snapshot.execution_archive_id
                    for snapshot in snapshots
                    if snapshot.execution_archive_id is not None
                    and snapshot.execution_archive_id not in archives_by_id
                },
            )
        )
        try:
            for run in runs:
                archive = archives.get(roots[("run", run.id)])
                if archive is not None:
                    self._hydrate_run(run, archive)
            for step in steps:
                root = roots.get(("step", step.id))
                archive = archives.get(root) if root is not None else None
                if archive is not None:
                    self._hydrate_step(step, archive)
            for snapshot in snapshots:
                if snapshot.execution_archive_id is None:
                    continue
                archive = archives_by_id.get(snapshot.execution_archive_id)
                if archive is not None:
                    self._hydrate_snapshot(
                        snapshot, archive, load_configurations
                    )
        except (ValueError, OSError) as e:
            # Undecodable or unreadable bytes; a bug in this module raises
            # as itself so it is not mistaken for a storage outage.
            raise ArchiveUnavailableError(
                f"Archived execution payload is unavailable: {e}"
            ) from e

    def _hydrate_run(
        self, run: PipelineRunSchema, archive: ExecutionArchiveResponse
    ) -> None:
        record = self._execution(archive).runs.get(run.id)
        if record is not None:
            overlay_absent_fields(run, record, ARCHIVED_RUN_FIELDS)

    def _hydrate_step(
        self, step: StepRunSchema, archive: ExecutionArchiveResponse
    ) -> None:
        dynamic_config = _loaded_dynamic_config(step)
        if has_absent_fields(step, ARCHIVED_STEP_FIELDS) or (
            dynamic_config is not None
            and dynamic_config.config == ARCHIVED_PAYLOAD_PLACEHOLDER
        ):
            execution = self._execution(archive)
            record = execution.steps.get(step.id)
            if record is not None:
                overlay_absent_fields(step, record, ARCHIVED_STEP_FIELDS)
            if dynamic_config is not None:
                _overlay_configuration(
                    dynamic_config, execution.configurations
                )
        static_config = _loaded_static_config(step)
        if static_config is not None:
            _overlay_configuration(
                static_config, self._snapshots(archive).configurations
            )

    def _hydrate_snapshot(
        self,
        snapshot: PipelineSnapshotSchema,
        archive: ExecutionArchiveResponse,
        load_configurations: bool,
    ) -> None:
        decoded = self._snapshots(archive)
        record = decoded.snapshots.get(snapshot.id)
        if record is not None:
            overlay_absent_fields(snapshot, record, ARCHIVED_SNAPSHOT_FIELDS)
        # Rows loaded later in the same session come from its identity map,
        # so overlaying the relationship covers every later lookup too.
        if load_configurations or is_loaded(snapshot, "step_configurations"):
            for configuration in snapshot.step_configurations:
                _overlay_configuration(configuration, decoded.configurations)

    def _execution(
        self, archive: ExecutionArchiveResponse
    ) -> DecodedExecution:
        def decode(raw: bytes) -> Decoded:
            return DecodedExecution.from_payload(
                ExecutionPayload.model_validate_json(raw)
            )

        return cast(
            DecodedExecution,
            self._load(
                archive,
                ArchiveObjectKind.EXECUTION,
                archive.execution_payload,
                decode,
            ),
        )

    def _snapshots(
        self, archive: ExecutionArchiveResponse
    ) -> DecodedSnapshots:
        def decode(raw: bytes) -> Decoded:
            return DecodedSnapshots.from_payload(
                SnapshotPayload.model_validate_json(raw)
            )

        return cast(
            DecodedSnapshots,
            self._load(
                archive,
                ArchiveObjectKind.SNAPSHOT,
                archive.snapshot_payload,
                decode,
            ),
        )

    def _load(
        self,
        archive: ExecutionArchiveResponse,
        kind: ArchiveObjectKind,
        object_: Optional[ExecutionArchiveObject],
        decode: Callable[[bytes], Decoded],
    ) -> Decoded:
        if object_ is None:
            raise ArchiveUnavailableError(
                f"Execution archive {archive.id} has no {kind.value} object."
            )
        reference = object_
        store = self._targets.object_store(archive.storage_target_id)

        def load() -> Tuple[Decoded, int]:
            raw = store.get_decompressed(kind, archive.project_id, reference)
            return decode(raw), _DECODED_WEIGHT_FACTOR * len(raw)

        return self._cache.get_or_load(reference.sha256, load)


def _run_needs_payload(run: PipelineRunSchema) -> bool:
    return has_absent_fields(run, ARCHIVED_RUN_FIELDS)


def _step_needs_payload(step: StepRunSchema) -> bool:
    dynamic_config = _loaded_dynamic_config(step)
    return (
        has_absent_fields(step, ARCHIVED_STEP_FIELDS)
        or (
            dynamic_config is not None
            and dynamic_config.config == ARCHIVED_PAYLOAD_PLACEHOLDER
        )
        or _loaded_static_config(step) is not None
    )


def _snapshot_needs_payload(
    snapshot: PipelineSnapshotSchema, load_configurations: bool
) -> bool:
    """Whether a snapshot or its configurations hold the placeholder.

    Only a snapshot an archive is authoritative for can hold archived
    configurations, so the marker decides before the configuration rows
    are ever loaded: a hot snapshot costs no query here.

    Args:
        snapshot: The snapshot.
        load_configurations: Whether its configurations are read too.

    Returns:
        Whether archived payload is needed.
    """
    if has_absent_fields(snapshot, ARCHIVED_SNAPSHOT_FIELDS):
        return True
    if not is_loaded(snapshot, "step_configurations") and (
        not load_configurations or snapshot.execution_archive_id is None
    ):
        return False
    return any(
        configuration.config == ARCHIVED_PAYLOAD_PLACEHOLDER
        for configuration in snapshot.step_configurations
    )


def _loaded_dynamic_config(
    step: StepRunSchema,
) -> Optional[StepConfigurationSchema]:
    return step.dynamic_config if is_loaded(step, "dynamic_config") else None


def _loaded_static_config(
    step: StepRunSchema,
) -> Optional[StepConfigurationSchema]:
    """The step's static configuration row, if loaded and archived.

    Args:
        step: The step run.

    Returns:
        The row holding the archive placeholder, or None.
    """
    if not is_loaded(step, "static_config"):
        return None
    static_config = step.static_config
    if (
        static_config is None
        or static_config.config != ARCHIVED_PAYLOAD_PLACEHOLDER
    ):
        return None
    return static_config


def _overlay_configuration(
    configuration: StepConfigurationSchema,
    records: Dict[UUID, ArchivedStepConfigurationPayload],
) -> None:
    record = records.get(configuration.id)
    if record is not None:
        overlay_absent_fields(
            configuration, record, ARCHIVED_CONFIGURATION_FIELDS
        )


def _family_roots(
    session: Session,
    runs: Sequence[PipelineRunSchema],
    steps: Sequence[StepRunSchema],
) -> Dict[Tuple[str, UUID], UUID]:
    """Map runs and step runs to the root run of their execution family.

    Runs know their root directly; step runs are resolved through the runs
    that own them with one query. Snapshots carry their archive directly.

    Args:
        session: The SQL session.
        runs: The runs.
        steps: The step runs.

    Returns:
        The family root of every row, keyed by kind and row ID.
    """
    roots: Dict[Tuple[str, UUID], UUID] = {
        ("run", run.id): run.root_run_id or run.id for run in runs
    }
    run_ids: Set[UUID] = {step.pipeline_run_id for step in steps}
    known = {run.id: run.root_run_id or run.id for run in runs}
    missing = [run_id for run_id in run_ids if run_id not in known]
    if missing:
        for run_id, root_run_id in session.exec(
            select(PipelineRunSchema.id, PipelineRunSchema.root_run_id).where(
                col(PipelineRunSchema.id).in_(missing)
            )
        ).all():
            known[run_id] = root_run_id or run_id
    for step in steps:
        root = known.get(step.pipeline_run_id)
        if root is not None:
            roots[("step", step.id)] = root
    return roots
