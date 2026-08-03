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
"""Tests for the dynamic pipeline entrypoint configuration."""

from typing import Any

import pytest

from zenml.constants import DYNAMIC_PIPELINE_RUN_FAILED_EXIT_CODE
from zenml.enums import ExecutionStatus
from zenml.models import PipelineRequest, PipelineSnapshotRequest
from zenml.pipelines.dynamic.entrypoint_configuration import (
    DynamicPipelineEntrypointConfiguration,
)


class _StubRun:
    """Stub run exposing only the status the entrypoint configuration reads."""

    def __init__(self, status: ExecutionStatus) -> None:
        self.status = status
        self.id = "stub-run-id"


class _FailingStubRunner:
    """Stub runner whose `run_pipeline` always raises."""

    def __init__(self, status: ExecutionStatus, **kwargs: Any) -> None:
        self.run = _StubRun(status=status)

    def run_pipeline(self) -> None:
        raise RuntimeError("boom")


def _create_snapshot(clean_client: Any) -> Any:
    pipeline = clean_client.zen_store.create_pipeline(
        PipelineRequest(
            name="pipeline",
            project=clean_client.active_project.id,
        )
    )
    request = PipelineSnapshotRequest(
        user=clean_client.active_user.id,
        project=clean_client.active_project.id,
        run_name_template="",
        pipeline_configuration={"name": "pipeline"},
        stack=clean_client.active_stack.id,
        client_version="0.12.3",
        server_version="0.12.3",
        pipeline=pipeline.id,
    )
    return clean_client.zen_store.create_snapshot(request)


def _entrypoint_config_with_stub_runner(
    clean_client: Any,
    monkeypatch: pytest.MonkeyPatch,
    status: ExecutionStatus,
) -> DynamicPipelineEntrypointConfiguration:
    snapshot = _create_snapshot(clean_client)

    monkeypatch.setattr(
        "zenml.pipelines.dynamic.entrypoint_configuration.DynamicPipelineRunner",
        lambda **kwargs: _FailingStubRunner(status=status, **kwargs),
    )
    monkeypatch.setattr(
        "zenml.pipelines.dynamic.entrypoint_configuration.integration_registry.activate_integrations",
        lambda: None,
    )
    monkeypatch.setattr(
        DynamicPipelineEntrypointConfiguration,
        "prepare_code_environment",
        lambda self: None,
    )

    return DynamicPipelineEntrypointConfiguration(
        arguments=["--snapshot_id", str(snapshot.id)]
    )


def test_run_exits_with_dedicated_code_when_run_reached_terminal_status(
    clean_client: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Tests that `run()` exits with the dedicated code once the run is terminal."""
    entrypoint_config = _entrypoint_config_with_stub_runner(
        clean_client, monkeypatch, status=ExecutionStatus.FAILED
    )

    with pytest.raises(SystemExit) as exc_info:
        entrypoint_config.run()

    assert exc_info.value.code == DYNAMIC_PIPELINE_RUN_FAILED_EXIT_CODE


def test_run_reraises_when_run_did_not_reach_terminal_status(
    clean_client: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Tests that `run()` re-raises the original exception when the run is not terminal."""
    entrypoint_config = _entrypoint_config_with_stub_runner(
        clean_client, monkeypatch, status=ExecutionStatus.RUNNING
    )

    with pytest.raises(RuntimeError, match="boom"):
        entrypoint_config.run()
