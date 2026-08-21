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
from typing import Any
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError
from sqlmodel import col, select

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
from zenml.zen_stores.sql_zen_store import Session, SqlZenStore


def _create_snapshot_context(
    client: Client,
) -> tuple[SqlZenStore, UUID, UUID, UUID]:
    store = client.zen_store
    assert isinstance(store, SqlZenStore)
    project_id = client.active_project.id
    stack_id = client.active_stack.id
    pipeline = store.create_pipeline(
        PipelineRequest(
            project=project_id,
            name=f"pipeline-{uuid4().hex[:8]}",
        )
    )
    return store, project_id, stack_id, pipeline.id


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
        is_dynamic=False,
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


def test_failed_snapshot_creation_leaves_no_snapshot(
    clean_client: Client,
) -> None:
    """A failed creation leaves the snapshot collection unchanged."""
    store, project_id, stack_id, pipeline_id = _create_snapshot_context(
        clean_client
    )
    request = _snapshot_request(
        project_id=project_id,
        stack_id=stack_id,
        pipeline_id=pipeline_id,
        name="new-snapshot",
        step_names=("first", "second"),
    )
    original_serializer = Step.model_dump_json

    def serialize(step: Step, *args: Any, **kwargs: Any) -> str:
        if step.config.name == "second":
            raise RuntimeError("injected step serialization failure")
        serialized = original_serializer(step, *args, **kwargs)
        assert isinstance(serialized, str)
        return serialized

    with patch.object(Step, "model_dump_json", serialize):
        with pytest.raises(
            RuntimeError, match="injected step serialization failure"
        ):
            store.create_snapshot(request)

    snapshots = store.list_snapshots(
        PipelineSnapshotFilter(project=project_id, named_only=False)
    )
    assert snapshots.items == []


def test_failed_snapshot_replacement_preserves_existing_snapshot(
    clean_client: Client,
) -> None:
    """A failed replacement preserves the existing named snapshot."""
    store, project_id, stack_id, pipeline_id = _create_snapshot_context(
        clean_client
    )
    existing = store.create_snapshot(
        _snapshot_request(
            project_id=project_id,
            stack_id=stack_id,
            pipeline_id=pipeline_id,
            name="saved-snapshot",
            step_names=("first",),
        )
    )
    replacement = _snapshot_request(
        project_id=project_id,
        stack_id=stack_id,
        pipeline_id=pipeline_id,
        name="saved-snapshot",
        step_names=("first", "second"),
        replace=True,
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

    snapshots = store.list_snapshots(
        PipelineSnapshotFilter(project=project_id, named_only=False)
    )
    assert [snapshot.id for snapshot in snapshots.items] == [existing.id]

    preserved = store.get_snapshot(existing.id)
    assert preserved.name == "saved-snapshot"
    assert preserved.step_configurations == existing.step_configurations


def test_replacing_unused_snapshot_discards_superseded_payload(
    clean_client: Client,
) -> None:
    """Repeated replacement retains only the latest unused snapshot."""
    store, project_id, stack_id, pipeline_id = _create_snapshot_context(
        clean_client
    )
    superseded_ids: list[UUID] = []

    for step_names in (("first",), ("first", "second"), ("latest",)):
        snapshot = store.create_snapshot(
            _snapshot_request(
                project_id=project_id,
                stack_id=stack_id,
                pipeline_id=pipeline_id,
                name="saved-snapshot",
                step_names=step_names,
                replace=bool(superseded_ids),
                tags=("snapshot-tag",),
            )
        )
        if superseded_ids:
            assert snapshot.id not in superseded_ids
        superseded_ids.append(snapshot.id)

    snapshots = store.list_snapshots(
        PipelineSnapshotFilter(project=project_id, named_only=False)
    )
    assert [snapshot.id for snapshot in snapshots.items] == [
        superseded_ids[-1]
    ]
    assert set(snapshots.items[0].step_configurations) == {"latest"}

    with Session(store.engine) as session:
        stale_step_configurations = session.exec(
            select(StepConfigurationSchema.id).where(
                col(StepConfigurationSchema.snapshot_id).in_(
                    superseded_ids[:-1]
                )
            )
        ).all()
        stale_tag_links = session.exec(
            select(TagResourceSchema.id).where(
                TagResourceSchema.resource_type
                == TaggableResourceTypes.PIPELINE_SNAPSHOT.value,
                col(TagResourceSchema.resource_id).in_(superseded_ids[:-1]),
            )
        ).all()
    assert stale_step_configurations == []
    assert stale_tag_links == []


def test_replacing_referenced_snapshot_preserves_run_history(
    clean_client: Client,
) -> None:
    """Replacement keeps an old snapshot that owns historical run data."""
    store, project_id, stack_id, pipeline_id = _create_snapshot_context(
        clean_client
    )
    existing = store.create_snapshot(
        _snapshot_request(
            project_id=project_id,
            stack_id=stack_id,
            pipeline_id=pipeline_id,
            name="saved-snapshot",
            step_names=("first",),
        )
    )
    run, _ = store.get_or_create_run(
        PipelineRunRequest(
            project=project_id,
            name="historical-run",
            snapshot=existing.id,
            status=ExecutionStatus.RUNNING,
        )
    )

    replacement = store.create_snapshot(
        _snapshot_request(
            project_id=project_id,
            stack_id=stack_id,
            pipeline_id=pipeline_id,
            name="saved-snapshot",
            step_names=("replacement",),
            replace=True,
        )
    )

    snapshots = store.list_snapshots(
        PipelineSnapshotFilter(project=project_id, named_only=False)
    )
    assert {snapshot.id for snapshot in snapshots.items} == {
        existing.id,
        replacement.id,
    }
    assert store.get_snapshot(existing.id).name is None
    preserved_run = store.get_run(run.id)
    assert preserved_run.snapshot is not None
    assert preserved_run.snapshot.id == existing.id


def test_replacing_snapshot_name_with_itself_keeps_snapshot(
    clean_client: Client,
) -> None:
    """Replacing an unchanged name does not discard the snapshot itself."""
    store, project_id, stack_id, pipeline_id = _create_snapshot_context(
        clean_client
    )
    existing = store.create_snapshot(
        _snapshot_request(
            project_id=project_id,
            stack_id=stack_id,
            pipeline_id=pipeline_id,
            name="saved-snapshot",
            step_names=("first",),
        )
    )

    updated = store.update_snapshot(
        existing.id,
        PipelineSnapshotUpdate(name="saved-snapshot", replace=True),
    )

    snapshots = store.list_snapshots(
        PipelineSnapshotFilter(project=project_id, named_only=False)
    )
    assert [snapshot.id for snapshot in snapshots.items] == [existing.id]
    assert updated.id == existing.id
    assert updated.name == "saved-snapshot"


def test_replacing_source_snapshot_preserves_derived_snapshot(
    clean_client: Client,
) -> None:
    """Replacement keeps a snapshot used as another snapshot's source."""
    store, project_id, stack_id, pipeline_id = _create_snapshot_context(
        clean_client
    )
    existing = store.create_snapshot(
        _snapshot_request(
            project_id=project_id,
            stack_id=stack_id,
            pipeline_id=pipeline_id,
            name="saved-snapshot",
            step_names=("first",),
        )
    )
    derived = store.create_snapshot(
        _snapshot_request(
            project_id=project_id,
            stack_id=stack_id,
            pipeline_id=pipeline_id,
            name="derived-snapshot",
            step_names=("derived",),
            source_snapshot=existing.id,
        )
    )

    replacement = store.create_snapshot(
        _snapshot_request(
            project_id=project_id,
            stack_id=stack_id,
            pipeline_id=pipeline_id,
            name="saved-snapshot",
            step_names=("replacement",),
            replace=True,
        )
    )

    assert store.get_snapshot(existing.id).name is None
    assert store.get_snapshot(derived.id).source_snapshot_id == existing.id
    assert replacement.name == "saved-snapshot"


def test_unreachable_snapshot_cleanup_is_explicit_and_conservative(
    clean_client: Client,
) -> None:
    """Cleanup deletes only old anonymous snapshots without references."""
    store, project_id, stack_id, pipeline_id = _create_snapshot_context(
        clean_client
    )

    def create_snapshot(name: str | None, tag: str) -> UUID:
        return store.create_snapshot(
            _snapshot_request(
                project_id=project_id,
                stack_id=stack_id,
                pipeline_id=pipeline_id,
                name=name,
                step_names=("step",),
                tags=(tag,),
            )
        ).id

    unreachable_id = create_snapshot(None, "unreachable")
    recent_id = create_snapshot(None, "recent")
    named_id = create_snapshot("saved", "named")
    referenced_id = create_snapshot(None, "referenced")
    store.get_or_create_run(
        PipelineRunRequest(
            project=project_id,
            name="historical-run",
            snapshot=referenced_id,
            status=ExecutionStatus.RUNNING,
        )
    )

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
    curated_visualization = store.create_curated_visualization(
        CuratedVisualizationRequest(
            project=project_id,
            artifact_visualization_id=artifact_visualization.id,
            resource_id=unreachable_id,
            resource_type=VisualizationResourceTypes.PIPELINE_SNAPSHOT,
        )
    )

    old_created = utc_now() - timedelta(days=60)
    cutoff = utc_now() - timedelta(days=30)
    with Session(store.engine) as session:
        for snapshot_id in (unreachable_id, named_id, referenced_id):
            snapshot = session.get(PipelineSnapshotSchema, snapshot_id)
            assert snapshot is not None
            snapshot.created = old_created
            session.add(snapshot)
        session.commit()

    assert store.cleanup_unreachable_snapshots(
        older_than=cutoff,
        batch_size=1,
    ) == (1, 0)
    assert store.get_snapshot(unreachable_id).id == unreachable_id

    assert store.cleanup_unreachable_snapshots(
        older_than=cutoff,
        batch_size=1,
        apply=True,
    ) == (1, 1)

    with pytest.raises(KeyError):
        store.get_snapshot(unreachable_id)
    with pytest.raises(KeyError):
        store.get_curated_visualization(curated_visualization.id)

    for retained_id in (recent_id, named_id, referenced_id):
        assert store.get_snapshot(retained_id).id == retained_id

    with Session(store.engine) as session:
        assert (
            session.exec(
                select(StepConfigurationSchema.id).where(
                    StepConfigurationSchema.snapshot_id == unreachable_id
                )
            ).all()
            == []
        )
        assert (
            session.exec(
                select(TagResourceSchema.id).where(
                    TagResourceSchema.resource_id == unreachable_id,
                    TagResourceSchema.resource_type
                    == TaggableResourceTypes.PIPELINE_SNAPSHOT.value,
                )
            ).all()
            == []
        )

    assert store.cleanup_unreachable_snapshots(
        older_than=cutoff,
        apply=True,
    ) == (0, 0)
