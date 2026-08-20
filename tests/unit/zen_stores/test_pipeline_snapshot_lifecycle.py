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

from typing import Any
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError

from zenml.client import Client
from zenml.config.source import Source, SourceType
from zenml.config.step_configurations import Step, StepConfiguration, StepSpec
from zenml.models import (
    PipelineRequest,
    PipelineSnapshotFilter,
    PipelineSnapshotRequest,
)
from zenml.zen_stores.sql_zen_store import SqlZenStore


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
    name: str,
    step_names: tuple[str, ...],
    replace: bool = False,
) -> PipelineSnapshotRequest:
    return PipelineSnapshotRequest(
        project=project_id,
        stack=stack_id,
        pipeline=pipeline_id,
        name=name,
        replace=replace,
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
