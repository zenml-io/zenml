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
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
"""Tests for pipeline snapshot lifecycle behavior in the SQL store."""

from datetime import timedelta
from functools import partial
from typing import Any, Callable
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, select

from zenml.client import Client
from zenml.config.source import Source, SourceType
from zenml.config.step_configurations import Step, StepConfiguration, StepSpec
from zenml.enums import (
    ArtifactSaveType,
    ArtifactType,
    ExecutionStatus,
    TaggableResourceTypes,
    VisualizationResourceTypes,
    VisualizationType,
)
from zenml.models import (
    ArtifactRequest,
    ArtifactVersionRequest,
    ArtifactVisualizationRequest,
    CuratedVisualizationRequest,
    PipelineRequest,
    PipelineRunRequest,
    PipelineSnapshotFilter,
    PipelineSnapshotRequest,
    PipelineSnapshotUpdate,
)
from zenml.utils.time_utils import utc_now
from zenml.zen_stores.schemas import (
    PipelineSnapshotSchema,
    StepConfigurationSchema,
    TagResourceSchema,
)
from zenml.zen_stores.sql_zen_store import SNAPSHOT_OWNER_COLUMNS, SqlZenStore

SnapshotRequestFactory = Callable[..., PipelineSnapshotRequest]

CUTOFF = utc_now() - timedelta(days=30)


@pytest.fixture
def store(clean_client: Client) -> SqlZenStore:
    """The SQL store backing the isolated test client."""
    store = clean_client.zen_store
    assert isinstance(store, SqlZenStore)
    return store


@pytest.fixture
def project_id(clean_client: Client) -> UUID:
    """The active project of the isolated test client."""
    return clean_client.active_project.id


@pytest.fixture
def snapshot_request(
    clean_client: Client, store: SqlZenStore, project_id: UUID
) -> SnapshotRequestFactory:
    """Factory for snapshot requests bound to a fresh pipeline."""
    pipeline = store.create_pipeline(
        PipelineRequest(project=project_id, name=f"pipeline-{uuid4().hex[:8]}")
    )
    return partial(
        _snapshot_request,
        project_id=project_id,
        stack_id=clean_client.active_stack.id,
        pipeline_id=pipeline.id,
    )


def _snapshot_request(
    *,
    project_id: UUID,
    stack_id: UUID,
    pipeline_id: UUID,
    name: str | None,
    step_names: tuple[str, ...],
    replace: bool = False,
    tags: tuple[str, ...] = (),
    source_snapshot: UUID | None = None,
) -> PipelineSnapshotRequest:
    return PipelineSnapshotRequest(
        project=project_id,
        stack=stack_id,
        pipeline=pipeline_id,
        name=name,
        replace=replace,
        tags=list(tags),
        source_snapshot=source_snapshot,
        run_name_template="",
        pipeline_configuration={"name": "pipeline"},
        client_version="test",
        server_version="test",
        step_configurations={
            step_name: Step(
                spec=StepSpec(
                    source=Source(
                        module="acme.steps",
                        type=SourceType.INTERNAL,
                    ),
                    upstream_steps=[],
                ),
                config=StepConfiguration(name=step_name),
            )
            for step_name in step_names
        },
    )


def _snapshot_ids(store: SqlZenStore, project_id: UUID) -> list[UUID]:
    snapshots = store.list_snapshots(
        PipelineSnapshotFilter(project=project_id, named_only=False)
    )
    return [snapshot.id for snapshot in snapshots.items]


def _owned_rows(
    store: SqlZenStore, snapshot_ids: list[UUID]
) -> tuple[list[UUID], list[UUID]]:
    """Return the step configuration and tag link IDs owned by snapshots."""
    with Session(store.engine) as session:
        step_configurations = session.exec(
            select(StepConfigurationSchema.id).where(
                col(StepConfigurationSchema.snapshot_id).in_(snapshot_ids)
            )
        ).all()
        tag_links = session.exec(
            select(TagResourceSchema.id).where(
                TagResourceSchema.resource_type
                == TaggableResourceTypes.PIPELINE_SNAPSHOT.value,
                col(TagResourceSchema.resource_id).in_(snapshot_ids),
            )
        ).all()
    return list(step_configurations), list(tag_links)


def _create_run(
    store: SqlZenStore, project_id: UUID, snapshot_id: UUID
) -> UUID:
    run, _ = store.get_or_create_run(
        PipelineRunRequest(
            project=project_id,
            name=f"run-{uuid4().hex[:8]}",
            snapshot=snapshot_id,
            status=ExecutionStatus.RUNNING,
        )
    )
    return run.id


def _backdate(store: SqlZenStore, *snapshot_ids: UUID) -> None:
    """Move snapshots past `CUTOFF`."""
    with Session(store.engine) as session:
        for snapshot_id in snapshot_ids:
            snapshot = session.get(PipelineSnapshotSchema, snapshot_id)
            assert snapshot is not None
            snapshot.created = CUTOFF - timedelta(days=30)
            session.add(snapshot)
        session.commit()


def _create_curated_visualization(
    store: SqlZenStore, project_id: UUID, snapshot_id: UUID
) -> UUID:
    artifact = store.create_artifact(
        ArtifactRequest(
            name=f"artifact-{uuid4().hex[:8]}",
            project=project_id,
            has_custom_name=True,
        )
    )
    artifact_version = store.create_artifact_version(
        ArtifactVersionRequest(
            artifact_id=artifact.id,
            project=project_id,
            version="1",
            type=ArtifactType.DATA,
            uri="s3://visualizations/snapshot.html",
            materializer=Source(
                module="acme.materializer", type=SourceType.INTERNAL
            ),
            data_type=Source(module="acme.data", type=SourceType.INTERNAL),
            save_type=ArtifactSaveType.STEP_OUTPUT,
            visualizations=[
                ArtifactVisualizationRequest(
                    type=VisualizationType.HTML,
                    uri="s3://visualizations/snapshot.html",
                )
            ],
        )
    )
    artifact_visualization = (artifact_version.visualizations or [])[0]
    return store.create_curated_visualization(
        CuratedVisualizationRequest(
            project=project_id,
            artifact_visualization_id=artifact_visualization.id,
            resource_id=snapshot_id,
            resource_type=VisualizationResourceTypes.PIPELINE_SNAPSHOT,
        )
    ).id


def test_failed_snapshot_creation_leaves_no_snapshot(
    store: SqlZenStore,
    project_id: UUID,
    snapshot_request: SnapshotRequestFactory,
) -> None:
    """A failed creation leaves the snapshot collection unchanged."""
    request = snapshot_request(
        name="new-snapshot", step_names=("first", "second")
    )
    original_serializer = Step.model_dump_json

    def serialize(step: Step, *args: Any, **kwargs: Any) -> str:
        if step.config.name == "second":
            raise RuntimeError("injected step serialization failure")
        return original_serializer(step, *args, **kwargs)

    with patch.object(Step, "model_dump_json", serialize):
        with pytest.raises(
            RuntimeError, match="injected step serialization failure"
        ):
            store.create_snapshot(request)

    assert _snapshot_ids(store, project_id) == []


def test_failed_snapshot_replacement_preserves_existing_snapshot(
    store: SqlZenStore,
    project_id: UUID,
    snapshot_request: SnapshotRequestFactory,
) -> None:
    """A failed replacement preserves the existing named snapshot."""
    existing = store.create_snapshot(
        snapshot_request(name="saved-snapshot", step_names=("first",))
    )
    replacement = snapshot_request(
        name="saved-snapshot", step_names=("first", "second"), replace=True
    )

    def fail_step_configuration_insert(
        connection: Any,
        cursor: Any,
        statement: str,
        parameters: Any,
        context: Any,
        executemany: bool,
    ) -> None:
        if (
            statement.lstrip()
            .lower()
            .startswith("insert into step_configuration")
        ):
            raise IntegrityError(
                statement,
                parameters,
                RuntimeError("injected step configuration write failure"),
            )

    event.listen(
        store.engine, "before_cursor_execute", fail_step_configuration_insert
    )
    try:
        with pytest.raises(RuntimeError, match="Snapshot creation failed"):
            store.create_snapshot(replacement)
    finally:
        event.remove(
            store.engine,
            "before_cursor_execute",
            fail_step_configuration_insert,
        )

    assert _snapshot_ids(store, project_id) == [existing.id]
    preserved = store.get_snapshot(existing.id)
    assert preserved.name == "saved-snapshot"
    assert preserved.step_configurations == existing.step_configurations


def test_replacing_unused_snapshot_discards_superseded_payload(
    store: SqlZenStore,
    project_id: UUID,
    snapshot_request: SnapshotRequestFactory,
) -> None:
    """Repeated replacement retains only the latest unused snapshot."""
    snapshot_ids: list[UUID] = []
    for step_names in (("first",), ("first", "second"), ("latest",)):
        snapshot = store.create_snapshot(
            snapshot_request(
                name="saved-snapshot",
                step_names=step_names,
                replace=bool(snapshot_ids),
                tags=("snapshot-tag",),
            )
        )
        snapshot_ids.append(snapshot.id)

    assert _snapshot_ids(store, project_id) == [snapshot_ids[-1]]
    assert set(store.get_snapshot(snapshot_ids[-1]).step_configurations) == {
        "latest"
    }
    assert _owned_rows(store, snapshot_ids[:-1]) == ([], [])


def test_replacing_referenced_snapshot_preserves_run_history(
    store: SqlZenStore,
    project_id: UUID,
    snapshot_request: SnapshotRequestFactory,
) -> None:
    """Replacement keeps an old snapshot that owns historical run data."""
    existing = store.create_snapshot(
        snapshot_request(name="saved-snapshot", step_names=("first",))
    )
    run_id = _create_run(store, project_id, existing.id)

    replacement = store.create_snapshot(
        snapshot_request(
            name="saved-snapshot", step_names=("replacement",), replace=True
        )
    )

    assert set(_snapshot_ids(store, project_id)) == {
        existing.id,
        replacement.id,
    }
    assert store.get_snapshot(existing.id).name is None
    preserved_run = store.get_run(run_id)
    assert preserved_run.snapshot is not None
    assert preserved_run.snapshot.id == existing.id


def test_replacing_snapshot_name_with_itself_keeps_snapshot(
    store: SqlZenStore,
    project_id: UUID,
    snapshot_request: SnapshotRequestFactory,
) -> None:
    """Replacing an unchanged name does not discard the snapshot itself."""
    existing = store.create_snapshot(
        snapshot_request(name="saved-snapshot", step_names=("first",))
    )

    updated = store.update_snapshot(
        existing.id,
        PipelineSnapshotUpdate(name="saved-snapshot", replace=True),
    )

    assert _snapshot_ids(store, project_id) == [existing.id]
    assert updated.id == existing.id
    assert updated.name == "saved-snapshot"


def test_replacing_source_snapshot_preserves_derived_snapshot(
    store: SqlZenStore,
    snapshot_request: SnapshotRequestFactory,
) -> None:
    """Replacement keeps a snapshot used as another snapshot's source."""
    existing = store.create_snapshot(
        snapshot_request(name="saved-snapshot", step_names=("first",))
    )
    derived = store.create_snapshot(
        snapshot_request(
            name="derived-snapshot",
            step_names=("derived",),
            source_snapshot=existing.id,
        )
    )

    replacement = store.create_snapshot(
        snapshot_request(
            name="saved-snapshot", step_names=("replacement",), replace=True
        )
    )

    assert store.get_snapshot(existing.id).name is None
    assert store.get_snapshot(derived.id).source_snapshot_id == existing.id
    assert replacement.name == "saved-snapshot"


def test_unreachable_snapshot_cleanup_is_explicit_and_conservative(
    store: SqlZenStore,
    project_id: UUID,
    snapshot_request: SnapshotRequestFactory,
) -> None:
    """Cleanup deletes only old anonymous snapshots without references."""

    def create_snapshot(name: str | None, tag: str) -> UUID:
        return store.create_snapshot(
            snapshot_request(name=name, step_names=("step",), tags=(tag,))
        ).id

    unreachable_id = create_snapshot(None, "unreachable")
    recent_id = create_snapshot(None, "recent")
    named_id = create_snapshot("saved", "named")
    referenced_id = create_snapshot(None, "referenced")
    _create_run(store, project_id, referenced_id)
    curated_visualization_id = _create_curated_visualization(
        store, project_id, unreachable_id
    )
    _backdate(store, unreachable_id, named_id, referenced_id)

    assert store.cleanup_unreachable_snapshots(CUTOFF, batch_size=1) == 1
    store.get_snapshot(unreachable_id)

    assert (
        store.cleanup_unreachable_snapshots(CUTOFF, batch_size=1, apply=True)
        == 1
    )

    with pytest.raises(KeyError):
        store.get_snapshot(unreachable_id)
    with pytest.raises(KeyError):
        store.get_curated_visualization(curated_visualization_id)
    assert _owned_rows(store, [unreachable_id]) == ([], [])
    for retained_id in (recent_id, named_id, referenced_id):
        store.get_snapshot(retained_id)

    assert store.cleanup_unreachable_snapshots(CUTOFF, apply=True) == 0


def test_cleanup_collects_a_source_chain_in_one_run(
    store: SqlZenStore,
    snapshot_request: SnapshotRequestFactory,
) -> None:
    """Snapshots freed by deleting their derived snapshot are also collected."""
    chain: list[UUID] = []
    for index in range(3):
        snapshot = store.create_snapshot(
            snapshot_request(
                name=None,
                step_names=(f"step-{index}",),
                source_snapshot=chain[-1] if chain else None,
            )
        )
        chain.append(snapshot.id)
    _backdate(store, *chain)

    # Only the leaf is unreferenced up front, so the dry run reports a single
    # pass while applying keeps rescanning until the chain is gone.
    assert store.cleanup_unreachable_snapshots(CUTOFF) == 1
    assert store.cleanup_unreachable_snapshots(CUTOFF, apply=True) == 3
    assert store.cleanup_unreachable_snapshots(CUTOFF, apply=True) == 0


def test_cleanup_retains_a_source_of_a_referenced_snapshot(
    store: SqlZenStore,
    project_id: UUID,
    snapshot_request: SnapshotRequestFactory,
) -> None:
    """A run anywhere in a chain keeps the whole chain alive."""
    source = store.create_snapshot(
        snapshot_request(name=None, step_names=("source",))
    )
    derived = store.create_snapshot(
        snapshot_request(
            name=None, step_names=("derived",), source_snapshot=source.id
        )
    )
    _create_run(store, project_id, derived.id)
    _backdate(store, source.id, derived.id)

    assert store.cleanup_unreachable_snapshots(CUTOFF, apply=True) == 0
    store.get_snapshot(source.id)
    store.get_snapshot(derived.id)


def test_snapshot_reference_check_covers_every_foreign_key() -> None:
    """Guard the reachability rule against schema drift.

    Deleting a snapshot cascades to its pipeline and step runs, so a new table
    referencing `pipeline_snapshot` that `SNAPSHOT_OWNER_COLUMNS` does not
    know about would silently destroy run history. `step_configuration` is
    excluded because it is data owned by the snapshot rather than a reference
    to it.
    """
    owned_tables = {"step_configuration"}
    foreign_key_columns = {
        f"{fk.parent.table.name}.{fk.parent.name}"
        for table in PipelineSnapshotSchema.metadata.tables.values()
        for fk in table.foreign_keys
        if fk.column.table.name == "pipeline_snapshot"
        and fk.parent.table.name not in owned_tables
    }
    owner_columns = {
        f"{column.expression.table.name}.{column.expression.name}"
        for column in SNAPSHOT_OWNER_COLUMNS
    }

    assert foreign_key_columns == owner_columns, (
        "Tables referencing `pipeline_snapshot` changed. Update "
        "`SNAPSHOT_OWNER_COLUMNS` in `sql_zen_store.py` accordingly."
    )
