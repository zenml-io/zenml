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
"""Schema-level round-trip tests for the hook invocation tables."""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterator
from uuid import uuid4

import pytest

from zenml.enums import ExecutionStatus, HookType
from zenml.models import ProjectFilter, UserFilter
from zenml.zen_stores.schemas import (
    ArtifactSchema,
    ArtifactVersionSchema,
    HookInvocationOutputArtifactSchema,
    HookInvocationSchema,
    PipelineRunSchema,
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


def test_hook_invocation_schema_round_trip(sql_store: SqlZenStore) -> None:
    """Test that a hook invocation and its output link round-trip."""
    project_id = (
        sql_store.list_projects(project_filter_model=ProjectFilter())
        .items[0]
        .id
    )
    user_id = sql_store.list_users(user_filter_model=UserFilter()).items[0].id

    start = datetime(2026, 1, 1, 0, 0, 0)
    end = start + timedelta(seconds=2)
    hook_id = uuid4()
    run_id = uuid4()
    version_id = uuid4()

    run = PipelineRunSchema(
        id=run_id,
        project_id=project_id,
        name="run-1",
        orchestrator_run_id=None,
        start_time=start,
        end_time=end,
        status=ExecutionStatus.COMPLETED.value,
        index=1,
        in_progress=False,
        enable_heartbeat=False,
        pipeline_id=None,
        snapshot_id=None,
        user_id=user_id,
    )

    with Session(sql_store.engine) as session:
        session.add(run)
        session.flush()

        artifact = ArtifactSchema(
            id=uuid4(),
            project_id=project_id,
            name="a",
            has_custom_name=False,
        )
        session.add(artifact)
        session.flush()

        version = ArtifactVersionSchema(
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
        session.add(version)
        session.flush()

        hook = HookInvocationSchema(
            id=hook_id,
            project_id=project_id,
            user_id=user_id,
            hook_type=HookType.CUSTOM.value,
            name="pre_tool_call",
            status=ExecutionStatus.COMPLETED.value,
            start_time=start,
            end_time=end,
            source="module.func",
            pipeline_run_id=run_id,
            step_run_id=None,
            exception_info='{"traceback": "boom"}',
        )
        session.add(hook)
        session.flush()

        session.add(
            HookInvocationOutputArtifactSchema(
                name="output",
                hook_invocation_id=hook_id,
                artifact_version_id=version_id,
            )
        )
        session.commit()

    with Session(sql_store.engine) as session:
        loaded = session.get(HookInvocationSchema, hook_id)
        assert loaded is not None
        assert loaded.hook_type == HookType.CUSTOM.value
        assert loaded.name == "pre_tool_call"
        assert loaded.status == ExecutionStatus.COMPLETED.value
        assert loaded.start_time == start
        assert loaded.end_time == end
        assert loaded.source == "module.func"
        assert loaded.pipeline_run_id == run_id
        assert loaded.step_run_id is None
        assert loaded.exception_info == '{"traceback": "boom"}'

        assert len(loaded.output_artifacts) == 1
        link = loaded.output_artifacts[0]
        assert link.name == "output"
        assert link.artifact_version_id == version_id
