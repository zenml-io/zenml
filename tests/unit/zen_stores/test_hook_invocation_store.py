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
"""Tests for hook invocation CRUD in SqlZenStore."""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterator
from uuid import UUID, uuid4

import pytest

from zenml.enums import ExecutionStatus, HookType, StackComponentType
from zenml.models import (
    ExceptionInfo,
    HookInvocationFilter,
    HookInvocationRequest,
    LogsRequest,
    ProjectFilter,
)
from zenml.zen_stores.schemas import (
    ArtifactSchema,
    ArtifactVersionSchema,
    HookInvocationOutputArtifactSchema,
    LogsSchema,
    PipelineRunSchema,
    StackComponentSchema,
    StepRunSchema,
)
from zenml.zen_stores.sql_zen_store import (
    Session,
    SqlZenStore,
    SqlZenStoreConfiguration,
)


@pytest.fixture
def sql_store(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[SqlZenStore]:
    """Create a fresh SQLite-backed SqlZenStore for tests."""
    db_dir = tmp_path / "zenml-cfg"
    db_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("ZENML_CONFIG_PATH", str(db_dir))
    db_path = db_dir / "test.db"
    config = SqlZenStoreConfiguration(url=f"sqlite:///{db_path}")
    store = SqlZenStore(config=config, skip_default_registrations=False)
    yield store


def _project_id(store: SqlZenStore) -> UUID:
    return (
        store.list_projects(project_filter_model=ProjectFilter()).items[0].id
    )


def _create_run(store: SqlZenStore, project_id: UUID, name: str) -> UUID:
    run_id = uuid4()
    run = PipelineRunSchema(
        id=run_id,
        project_id=project_id,
        name=name,
        orchestrator_run_id=None,
        start_time=None,
        end_time=None,
        status=ExecutionStatus.RUNNING.value,
        index=1,
        in_progress=True,
        enable_heartbeat=False,
        pipeline_id=None,
        snapshot_id=None,
        user_id=None,
    )
    with Session(store.engine) as session:
        session.add(run)
        session.commit()
    return run_id


def _create_step_run(
    store: SqlZenStore, project_id: UUID, run_id: UUID, name: str
) -> UUID:
    step_id = uuid4()
    step = StepRunSchema(
        id=step_id,
        project_id=project_id,
        pipeline_run_id=run_id,
        name=name,
        version=1,
        status=ExecutionStatus.COMPLETED.value,
        is_retriable=False,
    )
    with Session(store.engine) as session:
        session.add(step)
        session.commit()
    return step_id


def _create_artifact_version(store: SqlZenStore, project_id: UUID) -> UUID:
    version_id = uuid4()
    with Session(store.engine) as session:
        artifact = ArtifactSchema(
            id=uuid4(),
            project_id=project_id,
            name=f"art-{uuid4().hex[:8]}",
            has_custom_name=False,
        )
        session.add(artifact)
        session.flush()
        session.add(
            ArtifactVersionSchema(
                id=version_id,
                project_id=project_id,
                artifact_id=artifact.id,
                version="1",
                type="DataArtifact",
                uri="s3://x/1",
                materializer="m",
                data_type="d",
                save_type="step_output",
            )
        )
        session.commit()
    return version_id


def test_create_and_get_hook_invocation(sql_store: SqlZenStore) -> None:
    """Test creating and reading back a hook invocation."""
    project_id = _project_id(sql_store)
    run_id = _create_run(sql_store, project_id, "run-1")

    start = datetime(2026, 1, 1, 0, 0, 0)
    end = start + timedelta(seconds=3)
    request = HookInvocationRequest(
        project=project_id,
        hook_type=HookType.CUSTOM,
        name="pre_tool_call",
        status=ExecutionStatus.COMPLETED,
        start_time=start,
        end_time=end,
        source="module.func",
        pipeline_run_id=run_id,
    )
    created = sql_store.create_hook_invocation(request)

    assert created.hook_type == HookType.CUSTOM
    assert created.name == "pre_tool_call"
    assert created.status == ExecutionStatus.COMPLETED
    assert created.start_time == start
    assert created.end_time == end
    assert created.duration == timedelta(seconds=3)
    assert created.pipeline_run_id == run_id
    assert created.step_run_id is None
    assert created.source == "module.func"

    fetched = sql_store.get_hook_invocation(created.id)
    assert fetched.id == created.id
    assert fetched.name == "pre_tool_call"
    assert fetched.pipeline_run_id == run_id


def test_create_hook_invocation_records_exception_info(
    sql_store: SqlZenStore,
) -> None:
    """Test that a failed hook invocation persists exception info."""
    project_id = _project_id(sql_store)
    run_id = _create_run(sql_store, project_id, "run-1")

    request = HookInvocationRequest(
        project=project_id,
        hook_type=HookType.STEP_FAILURE,
        status=ExecutionStatus.FAILED,
        start_time=datetime(2026, 1, 1),
        end_time=datetime(2026, 1, 1),
        pipeline_run_id=run_id,
        exception_info=ExceptionInfo(traceback="boom", message="kaboom"),
    )
    created = sql_store.create_hook_invocation(request)

    fetched = sql_store.get_hook_invocation(created.id)
    assert fetched.status == ExecutionStatus.FAILED
    assert fetched.exception_info is not None
    assert fetched.exception_info.traceback == "boom"
    assert fetched.exception_info.message == "kaboom"
    assert fetched.name is None


def test_create_hook_invocation_links_outputs(
    sql_store: SqlZenStore,
) -> None:
    """Test that hook output artifact versions are linked."""
    project_id = _project_id(sql_store)
    run_id = _create_run(sql_store, project_id, "run-1")
    version_id = _create_artifact_version(sql_store, project_id)

    request = HookInvocationRequest(
        project=project_id,
        hook_type=HookType.CUSTOM,
        name="record",
        status=ExecutionStatus.COMPLETED,
        start_time=datetime(2026, 1, 1),
        end_time=datetime(2026, 1, 1),
        pipeline_run_id=run_id,
        outputs={"output": [version_id]},
    )
    created = sql_store.create_hook_invocation(request)

    assert set(created.outputs.keys()) == {"output"}
    assert [v.id for v in created.outputs["output"]] == [version_id]


def _artifact_store_id(store: SqlZenStore) -> UUID:
    with Session(store.engine) as session:
        component = (
            session.query(StackComponentSchema)
            .filter(
                StackComponentSchema.type
                == StackComponentType.ARTIFACT_STORE.value
            )
            .first()
        )
        assert component is not None
        return component.id


def _create_hook_logs(
    store: SqlZenStore, project_id: UUID, step_run_id: UUID
) -> UUID:
    logs = store.create_logs(
        LogsRequest(
            project=project_id,
            source="hook:custom:my_hook",
            uri="s3://bucket/hook-logs",
            artifact_store_id=_artifact_store_id(store),
            step_run_id=step_run_id,
        )
    )
    return logs.id


def test_create_hook_invocation_links_logs(sql_store: SqlZenStore) -> None:
    """Test that a logs entry links to the invocation and both run and hook."""
    project_id = _project_id(sql_store)
    run_id = _create_run(sql_store, project_id, "run-1")
    step_id = _create_step_run(sql_store, project_id, run_id, "train")
    logs_id = _create_hook_logs(sql_store, project_id, step_id)

    request = HookInvocationRequest(
        project=project_id,
        hook_type=HookType.CUSTOM,
        name="my_hook",
        status=ExecutionStatus.COMPLETED,
        start_time=datetime(2026, 1, 1),
        end_time=datetime(2026, 1, 1),
        pipeline_run_id=run_id,
        step_run_id=step_id,
        logs_id=logs_id,
    )
    created = sql_store.create_hook_invocation(request)

    # The logs entry links back to the invocation.
    assert sql_store.get_logs(logs_id).hook_invocation_id == created.id

    # The invocation response exposes the logs as a collection.
    assert created.log_collection is not None
    assert [log.id for log in created.log_collection] == [logs_id]
    fetched = sql_store.get_hook_invocation(created.id)
    assert [log.id for log in fetched.log_collection] == [logs_id]

    # The logs entry keeps its step run, so it also surfaces in the step's
    # log collection (which is built from logs carrying its step_run_id).
    with Session(sql_store.engine) as session:
        log = session.get(LogsSchema, logs_id)
        assert log is not None
        assert log.step_run_id == step_id
        assert log.hook_invocation_id == created.id


def test_delete_hook_invocation_unlinks_logs(sql_store: SqlZenStore) -> None:
    """Test that deleting a hook invocation unlinks but keeps its logs."""
    project_id = _project_id(sql_store)
    run_id = _create_run(sql_store, project_id, "run-1")
    step_id = _create_step_run(sql_store, project_id, run_id, "train")
    logs_id = _create_hook_logs(sql_store, project_id, step_id)

    request = HookInvocationRequest(
        project=project_id,
        hook_type=HookType.CUSTOM,
        name="my_hook",
        status=ExecutionStatus.COMPLETED,
        start_time=datetime(2026, 1, 1),
        end_time=datetime(2026, 1, 1),
        pipeline_run_id=run_id,
        step_run_id=step_id,
        logs_id=logs_id,
    )
    created = sql_store.create_hook_invocation(request)

    sql_store.delete_hook_invocation(created.id)

    # The logs entry survives, unlinked from the deleted invocation.
    surviving = sql_store.get_logs(logs_id)
    assert surviving.hook_invocation_id is None


def test_list_hook_invocations_filters(sql_store: SqlZenStore) -> None:
    """Test filtering hook invocations by run, type, name, and step."""
    project_id = _project_id(sql_store)
    run_a = _create_run(sql_store, project_id, "run-a")
    run_b = _create_run(sql_store, project_id, "run-b")
    step = _create_step_run(sql_store, project_id, run_a, "train")

    def _request(**overrides: object) -> HookInvocationRequest:
        kwargs = dict(
            project=project_id,
            hook_type=HookType.CUSTOM,
            status=ExecutionStatus.COMPLETED,
            start_time=datetime(2026, 1, 1),
            end_time=datetime(2026, 1, 1),
            pipeline_run_id=run_a,
        )
        kwargs.update(overrides)
        return HookInvocationRequest(**kwargs)

    sql_store.create_hook_invocation(_request(name="a"))
    sql_store.create_hook_invocation(
        _request(hook_type=HookType.RUN_START, name=None)
    )
    sql_store.create_hook_invocation(
        _request(hook_type=HookType.STEP_START, name=None, step_run_id=step)
    )
    sql_store.create_hook_invocation(_request(pipeline_run_id=run_b, name="b"))

    by_run_a = sql_store.list_hook_invocations(
        HookInvocationFilter(pipeline_run_id=run_a)
    )
    assert by_run_a.total == 3

    by_type = sql_store.list_hook_invocations(
        HookInvocationFilter(hook_type=HookType.CUSTOM.value)
    )
    assert by_type.total == 2

    by_name = sql_store.list_hook_invocations(HookInvocationFilter(name="a"))
    assert by_name.total == 1

    by_step = sql_store.list_hook_invocations(
        HookInvocationFilter(step_run_id=step)
    )
    assert by_step.total == 1
    assert by_step.items[0].hook_type == HookType.STEP_START


def test_delete_hook_invocation_unlinks_only(sql_store: SqlZenStore) -> None:
    """Test that deleting a hook removes the junction but not the artifact."""
    project_id = _project_id(sql_store)
    run_id = _create_run(sql_store, project_id, "run-1")
    version_id = _create_artifact_version(sql_store, project_id)

    request = HookInvocationRequest(
        project=project_id,
        hook_type=HookType.CUSTOM,
        name="record",
        status=ExecutionStatus.COMPLETED,
        start_time=datetime(2026, 1, 1),
        end_time=datetime(2026, 1, 1),
        pipeline_run_id=run_id,
        outputs={"output": [version_id]},
    )
    created = sql_store.create_hook_invocation(request)

    sql_store.delete_hook_invocation(created.id)

    with pytest.raises(KeyError):
        sql_store.get_hook_invocation(created.id)

    with Session(sql_store.engine) as session:
        links = session.query(HookInvocationOutputArtifactSchema).filter(
            HookInvocationOutputArtifactSchema.hook_invocation_id == created.id
        )
        assert links.count() == 0
        # The artifact version is left in place (unlink only).
        assert session.get(ArtifactVersionSchema, version_id) is not None


def test_prune_artifact_versions_retains_hook_outputs(
    sql_store: SqlZenStore,
) -> None:
    """Test that pruning keeps artifact versions referenced by hook outputs."""
    project_id = _project_id(sql_store)
    run_id = _create_run(sql_store, project_id, "run-1")
    version_id = _create_artifact_version(sql_store, project_id)

    request = HookInvocationRequest(
        project=project_id,
        hook_type=HookType.CUSTOM,
        name="record",
        status=ExecutionStatus.COMPLETED,
        start_time=datetime(2026, 1, 1),
        end_time=datetime(2026, 1, 1),
        pipeline_run_id=run_id,
        outputs={"output": [version_id]},
    )
    created = sql_store.create_hook_invocation(request)

    sql_store.prune_artifact_versions(project_id, only_versions=True)

    # The version is referenced only by the hook output, so it must survive.
    with Session(sql_store.engine) as session:
        assert session.get(ArtifactVersionSchema, version_id) is not None

    fetched = sql_store.get_hook_invocation(created.id)
    assert [v.id for v in fetched.outputs["output"]] == [version_id]
