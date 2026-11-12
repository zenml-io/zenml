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

from typing import Any, Callable
from unittest.mock import MagicMock

import pytest

from zenml.constants import UNRECOVERABLE_ORCHESTRATION_EXIT_CODE
from zenml.enums import ExecutionStatus
from zenml.models import PipelineRequest, PipelineSnapshotRequest
from zenml.pipelines.dynamic.entrypoint_configuration import (
    DynamicPipelineEntrypointConfiguration,
)
from zenml.pipelines.run_utils import create_placeholder_run


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
        run_name_template="test_run",
        pipeline_configuration={"name": "pipeline"},
        stack=clean_client.active_stack.id,
        client_version="0.12.3",
        server_version="0.12.3",
        pipeline=pipeline.id,
    )
    return clean_client.zen_store.create_snapshot(request)


def _entrypoint_config(
    monkeypatch: pytest.MonkeyPatch,
    snapshot: Any,
    runner_factory: Callable[..., Any],
    run: Any = None,
) -> DynamicPipelineEntrypointConfiguration:
    monkeypatch.setattr(
        "zenml.pipelines.dynamic.entrypoint_configuration.DynamicPipelineRunner",
        runner_factory,
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

    arguments = ["--snapshot_id", str(snapshot.id)]
    if run:
        arguments += ["--run_id", str(run.id)]
    return DynamicPipelineEntrypointConfiguration(arguments=arguments)


def _entrypoint_config_with_stub_runner(
    clean_client: Any,
    monkeypatch: pytest.MonkeyPatch,
    status: ExecutionStatus,
) -> DynamicPipelineEntrypointConfiguration:
    return _entrypoint_config(
        monkeypatch,
        snapshot=_create_snapshot(clean_client),
        runner_factory=lambda **kwargs: _FailingStubRunner(
            status=status, **kwargs
        ),
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

    assert exc_info.value.code == UNRECOVERABLE_ORCHESTRATION_EXIT_CODE


def test_run_reraises_when_run_did_not_reach_terminal_status(
    clean_client: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Tests that `run()` re-raises the original exception when the run is not terminal."""
    entrypoint_config = _entrypoint_config_with_stub_runner(
        clean_client, monkeypatch, status=ExecutionStatus.RUNNING
    )

    with pytest.raises(RuntimeError, match="boom"):
        entrypoint_config.run()


def test_run_fails_run_and_exits_on_unrecoverable_startup_error(
    clean_client: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Tests that a startup error that every retry would hit ends the run."""
    snapshot = _create_snapshot(clean_client)
    run = create_placeholder_run(snapshot=snapshot)
    entrypoint_config = _entrypoint_config(
        monkeypatch,
        snapshot=snapshot,
        run=run,
        runner_factory=MagicMock(
            side_effect=ModuleNotFoundError("No module named 'x'")
        ),
    )

    with pytest.raises(SystemExit) as exc_info:
        entrypoint_config.run()

    assert exc_info.value.code == UNRECOVERABLE_ORCHESTRATION_EXIT_CODE
    assert (
        clean_client.get_pipeline_run(run.id).status == ExecutionStatus.FAILED
    )


def test_run_reraises_recoverable_startup_error(
    clean_client: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Tests that a startup error that a retry might fix keeps the run."""
    snapshot = _create_snapshot(clean_client)
    run = create_placeholder_run(snapshot=snapshot)
    entrypoint_config = _entrypoint_config(
        monkeypatch,
        snapshot=snapshot,
        run=run,
        runner_factory=MagicMock(
            side_effect=RuntimeError("Server unavailable")
        ),
    )

    with pytest.raises(RuntimeError, match="Server unavailable"):
        entrypoint_config.run()

    assert clean_client.get_pipeline_run(run.id).status == run.status
