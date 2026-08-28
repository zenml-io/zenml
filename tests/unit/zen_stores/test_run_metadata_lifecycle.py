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
"""Tests for the run metadata lifecycle in the SQL store."""

from contextlib import contextmanager
from typing import Any, Callable, Iterator, Optional
from uuid import UUID, uuid4

import pytest
from sqlalchemy import event
from sqlalchemy.engine import Connection, Engine
from sqlmodel import Session, col, select

from zenml.client import Client
from zenml.config.pipeline_configurations import PipelineConfiguration
from zenml.config.source import Source, SourceType
from zenml.config.step_configurations import Step, StepConfiguration, StepSpec
from zenml.enums import (
    ArtifactSaveType,
    ArtifactType,
    ExecutionStatus,
    MetadataResourceTypes,
    RunWaitConditionType,
)
from zenml.metadata.metadata_types import MetadataTypeEnum
from zenml.models import (
    ArtifactRequest,
    ArtifactVersionRequest,
    ModelRequest,
    ModelVersionRequest,
    PipelineRequest,
    PipelineRunRequest,
    PipelineSnapshotRequest,
    RunMetadataRequest,
    RunMetadataResource,
    RunWaitConditionRequest,
    ScheduleRequest,
    StackResponse,
    StepRunRequest,
)
from zenml.utils.time_utils import utc_now
from zenml.zen_stores import sql_zen_store
from zenml.zen_stores.schemas import (
    PipelineRunSchema,
    RunMetadataResourceSchema,
    RunMetadataSchema,
)
from zenml.zen_stores.sql_zen_store import SqlZenStore

Resource = tuple[UUID, MetadataResourceTypes]


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
def stack(clean_client: Client) -> StackResponse:
    """The active stack of the isolated test client."""
    return clean_client.active_stack


@pytest.fixture
def snapshot_id(
    store: SqlZenStore, project_id: UUID, stack: StackResponse
) -> UUID:
    """A snapshot of a fresh pipeline that runs can be attached to."""
    return _create_snapshot(
        store, project_id, stack.id, _create_pipeline(store, project_id)
    )


def _create_pipeline(store: SqlZenStore, project_id: UUID) -> UUID:
    return store.create_pipeline(
        PipelineRequest(project=project_id, name=f"pipeline-{uuid4().hex[:8]}")
    ).id


def _create_snapshot(
    store: SqlZenStore, project_id: UUID, stack_id: UUID, pipeline_id: UUID
) -> UUID:
    return store.create_snapshot(
        PipelineSnapshotRequest(
            project=project_id,
            stack=stack_id,
            pipeline=pipeline_id,
            run_name_template="",
            pipeline_configuration=PipelineConfiguration(name="pipeline"),
            client_version="test",
            server_version="test",
            # Dynamic pipelines declare their steps at runtime and are the
            # only ones that can have wait conditions.
            is_dynamic=True,
        )
    ).id


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


def _create_step_run(
    store: SqlZenStore,
    project_id: UUID,
    run_id: UUID,
    original_step_run_id: Optional[UUID] = None,
) -> UUID:
    name = f"step-{uuid4().hex[:8]}"
    return store.create_run_step(
        StepRunRequest(
            project=project_id,
            name=name,
            pipeline_run_id=run_id,
            start_time=utc_now(),
            status=ExecutionStatus.CACHED
            if original_step_run_id
            else ExecutionStatus.COMPLETED,
            original_step_run_id=original_step_run_id,
            dynamic_config=Step(
                spec=StepSpec(
                    source=Source(module="acme", type=SourceType.INTERNAL),
                    upstream_steps=[],
                ),
                config=StepConfiguration(name=name),
            ),
        )
    ).id


def _create_wait_condition(
    store: SqlZenStore, project_id: UUID, run_id: UUID
) -> UUID:
    return store.create_run_wait_condition(
        RunWaitConditionRequest(
            project=project_id,
            run=run_id,
            name="wait",
            type=RunWaitConditionType.EXTERNAL_INPUT,
        )
    ).id


def _publish(
    store: SqlZenStore,
    project_id: UUID,
    resources: list[Resource],
    publisher_step_id: Optional[UUID] = None,
) -> UUID:
    """Publish one metadata value to `resources` and return its ID."""
    key = f"key-{uuid4().hex[:8]}"
    store.create_run_metadata(
        RunMetadataRequest(
            project=project_id,
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


def _metadata_exists(store: SqlZenStore, metadata_id: UUID) -> bool:
    with Session(store.engine) as session:
        return session.get(RunMetadataSchema, metadata_id) is not None


def _linked_resources(store: SqlZenStore, metadata_id: UUID) -> set[UUID]:
    with Session(store.engine) as session:
        return set(
            session.exec(
                select(RunMetadataResourceSchema.resource_id).where(
                    RunMetadataResourceSchema.run_metadata_id == metadata_id
                )
            ).all()
        )


def _create_orphan(store: SqlZenStore, project_id: UUID) -> UUID:
    """Create a metadata value that nothing links to."""
    orphan = RunMetadataSchema(
        project_id=project_id, key="orphan", value='"value"', type="str"
    )
    with Session(store.engine) as session:
        session.add(orphan)
        session.commit()
        return orphan.id


def _count_rows(store: SqlZenStore, schema: Any) -> int:
    with Session(store.engine) as session:
        return len(session.exec(select(schema.id)).all())


@contextmanager
def _failing_statements(engine: Engine, prefix: str) -> Iterator[None]:
    """Make every SQL statement that starts with `prefix` fail."""

    def fail(
        connection: Connection,
        cursor: Any,
        statement: str,
        parameters: Any,
        context: Any,
        executemany: bool,
    ) -> None:
        if statement.lstrip().lower().startswith(prefix):
            raise RuntimeError(f"injected failure on `{prefix}`")

    event.listen(engine, "before_cursor_execute", fail)
    try:
        yield
    finally:
        event.remove(engine, "before_cursor_execute", fail)


def test_metadata_publication_commits_once(
    store: SqlZenStore, project_id: UUID, snapshot_id: UUID
) -> None:
    """Publishing K values to R resources is one transaction, not K + K*R."""
    run_ids = [_create_run(store, project_id, snapshot_id) for _ in range(3)]
    keys = [f"key-{index}" for index in range(4)]
    commits = 0

    def count_commit(connection: Connection) -> None:
        nonlocal commits
        commits += 1

    # Counted at the engine level, so any other session using the engine
    # during the call would show up here as well.
    event.listen(store.engine, "commit", count_commit)
    try:
        store.create_run_metadata(
            RunMetadataRequest(
                project=project_id,
                resources=[
                    RunMetadataResource(
                        id=run_id, type=MetadataResourceTypes.PIPELINE_RUN
                    )
                    for run_id in run_ids
                ],
                values={key: 1.0 for key in keys},
                types={key: MetadataTypeEnum.FLOAT for key in keys},
            )
        )
    finally:
        event.remove(store.engine, "commit", count_commit)

    assert commits == 1
    assert _count_rows(store, RunMetadataSchema) == len(keys)
    assert _count_rows(store, RunMetadataResourceSchema) == len(keys) * len(
        run_ids
    )


def test_failed_metadata_publication_leaves_no_rows(
    store: SqlZenStore, project_id: UUID, snapshot_id: UUID
) -> None:
    """A request whose links cannot be written leaves no values behind."""
    run_id = _create_run(store, project_id, snapshot_id)

    with (
        _failing_statements(store.engine, "insert into run_metadata_resource"),
        pytest.raises(RuntimeError, match="injected failure"),
    ):
        _publish(
            store, project_id, [(run_id, MetadataResourceTypes.PIPELINE_RUN)]
        )

    assert _count_rows(store, RunMetadataSchema) == 0
    assert _count_rows(store, RunMetadataResourceSchema) == 0


def test_deleting_a_run_keeps_metadata_other_resources_still_use(
    store: SqlZenStore,
    project_id: UUID,
    snapshot_id: UUID,
    stack: StackResponse,
) -> None:
    """Values are deleted with their last link, not with their publisher."""
    run_id = _create_run(store, project_id, snapshot_id)
    step_id = _create_step_run(store, project_id, run_id)
    wait_id = _create_wait_condition(store, project_id, run_id)
    exclusive_id = _publish(
        store,
        project_id,
        [
            (run_id, MetadataResourceTypes.PIPELINE_RUN),
            (step_id, MetadataResourceTypes.STEP_RUN),
            (wait_id, MetadataResourceTypes.WAIT_CONDITION),
        ],
    )
    shared_id = _publish(
        store,
        project_id,
        [(step_id, MetadataResourceTypes.STEP_RUN)],
        publisher_step_id=step_id,
    )
    # A cached step run links to the values of the step it was cached from
    # instead of publishing them again.
    other_run_id = _create_run(store, project_id, snapshot_id)
    cached_step_id = _create_step_run(
        store, project_id, other_run_id, original_step_run_id=step_id
    )
    assert _linked_resources(store, shared_id) == {step_id, cached_step_id}
    artifact_version = _artifact_version(store, project_id, stack)
    shared_with_artifact_id = _publish(
        store,
        project_id,
        [(run_id, MetadataResourceTypes.PIPELINE_RUN), artifact_version],
    )
    orphan_id = _create_orphan(store, project_id)

    store.delete_run(run_id)

    assert not _metadata_exists(store, exclusive_id)
    assert _linked_resources(store, shared_id) == {cached_step_id}
    assert _linked_resources(store, shared_with_artifact_id) == {
        artifact_version[0]
    }
    # Only the metadata of the deleted resources is inspected.
    assert _metadata_exists(store, orphan_id)
    assert _count_rows(store, RunMetadataResourceSchema) == 2


def test_failed_run_deletion_keeps_run_and_metadata(
    store: SqlZenStore, project_id: UUID, snapshot_id: UUID
) -> None:
    """The run, its metadata and their links survive a failed deletion."""
    run_id = _create_run(store, project_id, snapshot_id)
    metadata_id = _publish(
        store, project_id, [(run_id, MetadataResourceTypes.PIPELINE_RUN)]
    )

    with (
        _failing_statements(store.engine, "delete from run_metadata "),
        pytest.raises(RuntimeError, match="injected failure"),
    ):
        store.delete_run(run_id)

    store.get_run(run_id)
    assert _linked_resources(store, metadata_id) == {run_id}


def test_deleting_a_snapshot_or_pipeline_reaps_the_metadata_of_its_runs(
    store: SqlZenStore, project_id: UUID, stack: StackResponse
) -> None:
    """Cascading run deletions clean up metadata like direct ones."""
    pipeline_id = _create_pipeline(store, project_id)
    snapshot_ids = [
        _create_snapshot(store, project_id, stack.id, pipeline_id)
        for _ in range(2)
    ]
    run_ids = [
        _create_run(store, project_id, snapshot_id)
        for snapshot_id in snapshot_ids
    ]
    survivor_run_id = _create_run(
        store,
        project_id,
        _create_snapshot(
            store, project_id, stack.id, _create_pipeline(store, project_id)
        ),
    )
    exclusive_ids = [
        _publish(
            store, project_id, [(run_id, MetadataResourceTypes.PIPELINE_RUN)]
        )
        for run_id in run_ids
    ]
    shared_id = _publish(
        store,
        project_id,
        [
            (run_id, MetadataResourceTypes.PIPELINE_RUN)
            for run_id in (*run_ids, survivor_run_id)
        ],
    )

    # Schedules are deleted with their pipeline by the database, not the ORM.
    schedule_id = store.create_schedule(
        ScheduleRequest(
            name="schedule",
            cron_expression="*/5 * * * *",
            project=project_id,
            orchestrator_id=stack.orchestrator.id,
            pipeline_id=pipeline_id,
            active=False,
        )
    ).id
    schedule_metadata_id = _publish(
        store, project_id, [(schedule_id, MetadataResourceTypes.SCHEDULE)]
    )

    store.delete_snapshot(snapshot_ids[0])
    assert not _metadata_exists(store, exclusive_ids[0])
    assert _metadata_exists(store, exclusive_ids[1])

    store.delete_pipeline(pipeline_id)
    assert not _metadata_exists(store, exclusive_ids[1])
    assert not _metadata_exists(store, schedule_metadata_id)

    with Session(store.engine) as session:
        assert session.get(PipelineRunSchema, run_ids[1]) is None
    assert _linked_resources(store, shared_id) == {survivor_run_id}


def _artifact_version(
    store: SqlZenStore, project_id: UUID, stack: StackResponse
) -> Resource:
    artifact = store.create_artifact(
        ArtifactRequest(
            name=f"artifact-{uuid4().hex[:8]}",
            has_custom_name=True,
            project=project_id,
        )
    )
    version = store.create_artifact_version(
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
    )
    return version.id, MetadataResourceTypes.ARTIFACT_VERSION


def _model_version(
    store: SqlZenStore, project_id: UUID, stack: StackResponse
) -> Resource:
    model = store.create_model(
        ModelRequest(name=f"model-{uuid4().hex[:8]}", project=project_id)
    )
    version = store.create_model_version(
        ModelVersionRequest(model=model.id, project=project_id)
    )
    return version.id, MetadataResourceTypes.MODEL_VERSION


def _schedule(
    store: SqlZenStore, project_id: UUID, stack: StackResponse
) -> Resource:
    schedule = store.create_schedule(
        ScheduleRequest(
            name=f"schedule-{uuid4().hex[:8]}",
            cron_expression="*/5 * * * *",
            project=project_id,
            orchestrator_id=stack.orchestrator.id,
            pipeline_id=_create_pipeline(store, project_id),
            active=False,
        )
    )
    return schedule.id, MetadataResourceTypes.SCHEDULE


def _delete_artifact(store: SqlZenStore, version_id: UUID) -> None:
    store.delete_artifact(store.get_artifact_version(version_id).artifact.id)


def _prune_artifact_versions(store: SqlZenStore, version_id: UUID) -> None:
    store.prune_artifact_versions(
        store.get_artifact_version(version_id).project_id
    )


def _delete_model(store: SqlZenStore, version_id: UUID) -> None:
    store.delete_model(store.get_model_version(version_id).model.id)


@pytest.mark.parametrize(
    "create_resource, delete_resource",
    [
        (_artifact_version, SqlZenStore.delete_artifact_version),
        (_artifact_version, _delete_artifact),
        (_artifact_version, _prune_artifact_versions),
        (_model_version, SqlZenStore.delete_model_version),
        (_model_version, _delete_model),
        (_schedule, SqlZenStore.delete_schedule),
    ],
    ids=lambda function: function.__name__.strip("_"),
)
def test_deleting_other_resources_reaps_their_metadata(
    store: SqlZenStore,
    project_id: UUID,
    snapshot_id: UUID,
    stack: StackResponse,
    create_resource: Callable[[SqlZenStore, UUID, StackResponse], Resource],
    delete_resource: Callable[[SqlZenStore, UUID], None],
) -> None:
    """Every deletion path of a metadata-carrying resource reaps values."""
    resource_id, resource_type = create_resource(store, project_id, stack)
    run_id = _create_run(store, project_id, snapshot_id)
    exclusive_id = _publish(store, project_id, [(resource_id, resource_type)])
    shared_id = _publish(
        store,
        project_id,
        [
            (resource_id, resource_type),
            (run_id, MetadataResourceTypes.PIPELINE_RUN),
        ],
    )

    delete_resource(store, resource_id)

    assert not _metadata_exists(store, exclusive_id)
    assert _linked_resources(store, shared_id) == {run_id}
    assert _count_rows(store, RunMetadataResourceSchema) == 1


def test_cleanup_handles_id_lists_larger_than_one_batch(
    store: SqlZenStore,
    project_id: UUID,
    snapshot_id: UUID,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Resource and metadata IDs are chunked without losing any of them."""
    monkeypatch.setattr(sql_zen_store, "SQL_IN_CLAUSE_BATCH_SIZE", 1)
    run_id = _create_run(store, project_id, snapshot_id)
    step_ids = [_create_step_run(store, project_id, run_id) for _ in range(3)]
    for step_id in step_ids:
        _publish(
            store, project_id, [(step_id, MetadataResourceTypes.STEP_RUN)]
        )

    store.delete_run(run_id)

    assert _count_rows(store, RunMetadataSchema) == 0
    assert _count_rows(store, RunMetadataResourceSchema) == 0
