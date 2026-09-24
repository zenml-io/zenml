#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
"""Tests for publishing and deleting run metadata in the SQL store.

The deletion of each resource type is covered by
`TestRunMetadata.test_metadata_full_cycle_with_cascade_deletion`.
"""

from typing import Any, Optional, Tuple
from uuid import UUID, uuid4

import pytest
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from zenml.client import Client
from zenml.config.pipeline_configurations import PipelineConfiguration
from zenml.config.source import Source, SourceType
from zenml.config.step_configurations import Step, StepConfiguration, StepSpec
from zenml.enums import (
    ArtifactSaveType,
    ArtifactType,
    ExecutionStatus,
    MetadataResourceTypes,
)
from zenml.metadata.metadata_types import MetadataTypeEnum
from zenml.models import (
    ArtifactRequest,
    ArtifactVersionRequest,
    ModelRequest,
    ModelVersionArtifactRequest,
    ModelVersionRequest,
    PipelineRequest,
    PipelineRunRequest,
    PipelineSnapshotRequest,
    RunMetadataRequest,
    RunMetadataResource,
    StepRunRequest,
)
from zenml.utils.time_utils import utc_now
from zenml.zen_stores import sql_zen_store
from zenml.zen_stores.schemas import (
    RunMetadataResourceSchema,
    RunMetadataSchema,
)
from zenml.zen_stores.sql_zen_store import SqlZenStore


@pytest.fixture
def store(clean_client: Client) -> SqlZenStore:
    """The SQL store backing the isolated test client."""
    store = clean_client.zen_store
    assert isinstance(store, SqlZenStore)
    return store


def _create_run(store: SqlZenStore) -> UUID:
    project_id = Client().active_project.id
    pipeline = store.create_pipeline(
        PipelineRequest(project=project_id, name=f"p-{uuid4().hex[:8]}")
    )
    snapshot = store.create_snapshot(
        PipelineSnapshotRequest(
            project=project_id,
            stack=Client().active_stack.id,
            pipeline=pipeline.id,
            run_name_template="",
            pipeline_configuration=PipelineConfiguration(name="pipeline"),
            client_version="test",
            server_version="test",
            is_dynamic=True,
        )
    )
    run, _ = store.get_or_create_run(
        PipelineRunRequest(
            project=project_id,
            name=f"run-{uuid4().hex[:8]}",
            snapshot=snapshot.id,
            status=ExecutionStatus.RUNNING,
        )
    )
    return run.id


def _create_step_run(
    store: SqlZenStore, run_id: UUID, cached_from: Optional[UUID] = None
) -> UUID:
    name = f"step-{uuid4().hex[:8]}"
    return store.create_run_step(
        StepRunRequest(
            project=Client().active_project.id,
            name=name,
            pipeline_run_id=run_id,
            start_time=utc_now(),
            status=ExecutionStatus.CACHED
            if cached_from
            else ExecutionStatus.COMPLETED,
            original_step_run_id=cached_from,
            dynamic_config=Step(
                spec=StepSpec(
                    source=Source(module="acme", type=SourceType.INTERNAL),
                    upstream_steps=[],
                ),
                config=StepConfiguration(name=name),
            ),
        )
    ).id


def _create_artifact_version(store: SqlZenStore) -> UUID:
    project_id = Client().active_project.id
    artifact = store.create_artifact(
        ArtifactRequest(
            name=f"a-{uuid4().hex[:8]}",
            has_custom_name=True,
            project=project_id,
        )
    )
    return store.create_artifact_version(
        ArtifactVersionRequest(
            artifact_id=artifact.id,
            project=project_id,
            version="1",
            type=ArtifactType.DATA,
            uri=f"uri-{uuid4().hex[:8]}",
            materializer=Source(module="acme", type=SourceType.INTERNAL),
            data_type=Source(module="acme", type=SourceType.INTERNAL),
            save_type=ArtifactSaveType.STEP_OUTPUT,
        )
    ).id


def _publish(
    store: SqlZenStore,
    *resources: Tuple[UUID, MetadataResourceTypes],
    publisher_step_id: Optional[UUID] = None,
) -> UUID:
    """Publish one metadata value for resources and return the value ID."""
    key = f"key-{uuid4().hex[:8]}"
    store.create_run_metadata(
        RunMetadataRequest(
            project=Client().active_project.id,
            resources=[
                RunMetadataResource(id=resource_id, type=resource_type)
                for resource_id, resource_type in resources
            ],
            values={key: "value"},
            types={key: MetadataTypeEnum.STRING},
            publisher_step_id=publisher_step_id,
        )
    )
    with Session(store.engine) as session:
        return session.exec(
            select(RunMetadataSchema.id).where(RunMetadataSchema.key == key)
        ).one()


def _count(store: SqlZenStore, schema: Any) -> int:
    with Session(store.engine) as session:
        return len(session.exec(select(schema.id)).all())


def test_failed_metadata_publication_leaves_no_rows(
    store: SqlZenStore,
) -> None:
    """Values and links of a request are committed together or not at all."""
    run_id = _create_run(store)

    def fail_link_insert(_c: Any, _cur: Any, statement: str, *_: Any) -> None:
        if statement.lower().startswith("insert into run_metadata_resource"):
            raise RuntimeError("link insert failed")

    event.listen(store.engine, "before_cursor_execute", fail_link_insert)
    try:
        with pytest.raises(RuntimeError, match="link insert failed"):
            _publish(store, (run_id, MetadataResourceTypes.PIPELINE_RUN))
    finally:
        event.remove(store.engine, "before_cursor_execute", fail_link_insert)

    assert _count(store, RunMetadataSchema) == 0
    assert _count(store, RunMetadataResourceSchema) == 0


def test_deleting_a_run_keeps_values_a_cached_step_still_uses(
    store: SqlZenStore,
) -> None:
    """A value is deleted with its last link, not with its publisher."""
    run_id = _create_run(store)
    step_id = _create_step_run(store, run_id)
    exclusive_id = _publish(
        store, (run_id, MetadataResourceTypes.PIPELINE_RUN)
    )
    shared_id = _publish(
        store,
        (step_id, MetadataResourceTypes.STEP_RUN),
        publisher_step_id=step_id,
    )
    # A cache hit links the new step run to the values of the original one.
    cached_run_id = _create_run(store)
    cached_step_id = _create_step_run(
        store, cached_run_id, cached_from=step_id
    )

    store.delete_run(run_id)

    with Session(store.engine) as session:
        assert session.get(RunMetadataSchema, exclusive_id) is None
        assert session.exec(
            select(RunMetadataResourceSchema.resource_id).where(
                RunMetadataResourceSchema.run_metadata_id == shared_id
            )
        ).all() == [cached_step_id]

    store.delete_run(cached_run_id)

    assert _count(store, RunMetadataSchema) == 0


def test_cached_step_run_survives_losing_its_metadata(
    store: SqlZenStore,
) -> None:
    """A cache hit whose original run is being deleted still succeeds."""
    step_id = _create_step_run(store, _create_run(store))
    _publish(
        store,
        (step_id, MetadataResourceTypes.STEP_RUN),
        publisher_step_id=step_id,
    )

    def fail_link_insert(_c: Any, _cur: Any, statement: str, *_: Any) -> None:
        if statement.lower().startswith("insert into run_metadata_resource"):
            raise IntegrityError(statement, None, Exception("deleted value"))

    event.listen(store.engine, "before_cursor_execute", fail_link_insert)
    try:
        cached_step_id = _create_step_run(
            store, _create_run(store), cached_from=step_id
        )
    finally:
        event.remove(store.engine, "before_cursor_execute", fail_link_insert)

    assert store.get_run_step(cached_step_id).status == ExecutionStatus.CACHED


@pytest.mark.parametrize("path", ["prune", "model_version_links"])
def test_bulk_artifact_version_deletion_deletes_metadata(
    store: SqlZenStore, path: str
) -> None:
    """Bulk deletes of artifact versions also delete their metadata."""
    version_id = _create_artifact_version(store)
    _publish(store, (version_id, MetadataResourceTypes.ARTIFACT_VERSION))

    if path == "prune":
        store.prune_artifact_versions(Client().active_project.id)
    else:
        model = store.create_model(
            ModelRequest(
                name=f"m-{uuid4().hex[:8]}", project=Client().active_project.id
            )
        )
        model_version = store.create_model_version(
            ModelVersionRequest(
                model=model.id, project=Client().active_project.id
            )
        )
        store.create_model_version_artifact_link(
            ModelVersionArtifactRequest(
                model_version=model_version.id, artifact_version=version_id
            )
        )
        store.delete_all_model_version_artifact_links(
            model_version.id, only_links=False
        )

    assert _count(store, RunMetadataSchema) == 0
    assert _count(store, RunMetadataResourceSchema) == 0


def test_deletion_handles_more_ids_than_one_batch(
    store: SqlZenStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A value linked from several batches is deleted with its last link."""
    monkeypatch.setattr(sql_zen_store, "SQL_IN_CLAUSE_BATCH_SIZE", 1)
    run_id = _create_run(store)
    step_ids = [_create_step_run(store, run_id) for _ in range(3)]
    _publish(
        store, *((id_, MetadataResourceTypes.STEP_RUN) for id_ in step_ids)
    )

    store.delete_run(run_id)

    assert _count(store, RunMetadataSchema) == 0
    assert _count(store, RunMetadataResourceSchema) == 0
