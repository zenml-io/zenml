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
"""Unit tests for the dynamic pipeline runner."""

from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import PropertyMock
from uuid import uuid4

import pytest

from zenml.enums import ExecutionStatus
from zenml.exceptions import HookExecutionException
from zenml.execution.pipeline.dynamic.runner import DynamicPipelineRunner
from zenml.models import PipelineRunTriggerInfo
from zenml.orchestrators.base_orchestrator import BaseOrchestrator
from zenml.steps.step_context import run_context_exists


def _pipeline_configuration(*, init_hook_source=None):
    return SimpleNamespace(
        name="dynamic_pipeline",
        environment={},
        init_hook_source=init_hook_source,
        init_hook_kwargs={},
        cleanup_hook_source=None,
    )


def _make_runner(
    mocker,
    *,
    triggered_by_deployment: bool,
    trigger_info=None,
):
    runner = DynamicPipelineRunner.__new__(DynamicPipelineRunner)
    runner._state = SimpleNamespace(id=None)
    runner._snapshot = SimpleNamespace(
        pipeline_configuration=_pipeline_configuration(),
        stack=SimpleNamespace(),
    )
    runner._run = SimpleNamespace(
        id=uuid4(),
        status=ExecutionStatus.RUNNING,
        triggered_by_deployment=triggered_by_deployment,
        trigger_info=trigger_info,
    )
    runner._orchestrator = mocker.MagicMock()
    runner._executor = mocker.MagicMock()
    runner._shutdown_requested = False
    runner._startup_event = mocker.MagicMock()
    runner._monitoring_event = mocker.MagicMock()
    runner._pause_coordinator = mocker.MagicMock()

    mocker.patch(
        "zenml.execution.pipeline.dynamic.runner.is_pipeline_logging_enabled",
        return_value=False,
    )
    mocker.patch(
        "zenml.execution.pipeline.dynamic.runner.InMemoryArtifactCache",
        return_value=nullcontext(),
    )
    mocker.patch(
        "zenml.execution.pipeline.dynamic.runner.env_utils.temporary_runtime_environment",
        return_value=nullcontext(),
    )
    mocker.patch(
        "zenml.execution.pipeline.dynamic.runner.DynamicPipelineRunContext",
        return_value=nullcontext(),
    )
    mocker.patch.object(
        DynamicPipelineRunner,
        "pipeline",
        new_callable=PropertyMock,
        return_value=mocker.MagicMock(
            configuration=SimpleNamespace(parameters={})
        ),
    )
    return runner


def _patch_background_threads(mocker, runner):
    monitoring_thread = mocker.MagicMock()
    startup_thread = mocker.MagicMock()
    mocker.patch.object(
        runner, "_start_monitoring_loop", return_value=monitoring_thread
    )
    mocker.patch.object(
        runner, "_start_startup_loop", return_value=startup_thread
    )
    return monitoring_thread, startup_thread


def test_dynamic_runner_clears_partial_run_context_when_init_raises(
    mocker,
):
    runner = _make_runner(mocker, triggered_by_deployment=False)
    runner._snapshot.pipeline_configuration = _pipeline_configuration(
        init_hook_source="module.init_hook"
    )
    runner._orchestrator.run_init_hook.side_effect = (
        BaseOrchestrator.run_init_hook
    )
    runner._orchestrator.run_cleanup_hook.side_effect = (
        BaseOrchestrator.run_cleanup_hook
    )
    monitoring_thread, startup_thread = _patch_background_threads(
        mocker, runner
    )
    mock_run_entrypoint = mocker.patch.object(
        runner, "_run_entrypoint_and_finalize"
    )
    mocker.patch(
        "zenml.orchestrators.base_orchestrator.load_and_run_hook",
        side_effect=RuntimeError("init failed"),
    )

    with pytest.raises(HookExecutionException, match="Failed to execute"):
        runner.run_pipeline()

    assert run_context_exists() is False
    runner._orchestrator.run_init_hook.assert_called_once_with(
        snapshot=runner._snapshot
    )
    runner._orchestrator.run_cleanup_hook.assert_called_once_with(
        snapshot=runner._snapshot
    )
    mock_run_entrypoint.assert_not_called()
    runner._executor.shutdown.assert_called_once_with(
        wait=True, cancel_futures=True
    )
    assert runner._shutdown_requested is True
    runner._startup_event.set.assert_called_once_with()
    runner._monitoring_event.set.assert_called_once_with()
    monitoring_thread.join.assert_called_once_with()
    startup_thread.join.assert_called_once_with()
    runner._pause_coordinator.unregister.assert_called_once_with(runner)


def test_dynamic_runner_shuts_down_monitoring_when_startup_loop_fails(
    mocker,
):
    runner = _make_runner(mocker, triggered_by_deployment=False)
    monitoring_thread = mocker.MagicMock()
    mocker.patch.object(
        runner, "_start_monitoring_loop", return_value=monitoring_thread
    )
    mocker.patch.object(
        runner,
        "_start_startup_loop",
        side_effect=RuntimeError("startup failed"),
    )

    with pytest.raises(RuntimeError, match="startup failed"):
        runner.run_pipeline()

    runner._orchestrator.run_init_hook.assert_not_called()
    runner._orchestrator.run_cleanup_hook.assert_not_called()
    runner._executor.shutdown.assert_called_once_with(
        wait=True, cancel_futures=True
    )
    assert runner._shutdown_requested is True
    runner._startup_event.set.assert_called_once_with()
    runner._monitoring_event.set.assert_called_once_with()
    monitoring_thread.join.assert_called_once_with()
    runner._pause_coordinator.unregister.assert_called_once_with(runner)


def test_dynamic_runner_passes_parent_trigger_info_to_child_runs(
    mocker,
):
    trigger_info = PipelineRunTriggerInfo(deployment_id=uuid4())
    runner = _make_runner(
        mocker,
        triggered_by_deployment=True,
        trigger_info=trigger_info,
    )
    runner._existing_child_runs = {}
    runner._orchestrator_run_id = "orchestrator-run-id"
    child_snapshot = mocker.MagicMock()
    child_run = mocker.MagicMock()
    mock_compile_child_pipeline = mocker.patch(
        "zenml.execution.pipeline.dynamic.runner.compile_child_pipeline",
        return_value=child_snapshot,
    )
    mock_create_placeholder_run = mocker.patch(
        "zenml.execution.pipeline.dynamic.runner.create_placeholder_run",
        return_value=child_run,
    )
    pipeline = mocker.MagicMock()

    result = runner._prepare_child_run(
        pipeline=pipeline,
        args=("arg",),
        kwargs={"parameter": "value"},
        after=None,
        child_invocation_id="pipeline:child",
    )

    assert result is child_run
    mock_compile_child_pipeline.assert_called_once_with(
        pipeline=pipeline,
        args=("arg",),
        kwargs={"parameter": "value"},
        parent_snapshot=runner._snapshot,
    )
    mock_create_placeholder_run.assert_called_once_with(
        snapshot=child_snapshot,
        orchestrator_run_id="orchestrator-run-id",
        trigger_info=trigger_info,
        parent_run_id=runner._run.id,
        child_key="pipeline:child",
    )


def test_dynamic_runner_skips_lifecycle_hooks_for_deployment_runs(
    mocker,
):
    runner = _make_runner(mocker, triggered_by_deployment=True)
    monitoring_thread, startup_thread = _patch_background_threads(
        mocker, runner
    )
    mock_run_entrypoint = mocker.patch.object(
        runner, "_run_entrypoint_and_finalize"
    )

    runner.run_pipeline()

    runner._orchestrator.run_init_hook.assert_not_called()
    runner._orchestrator.run_cleanup_hook.assert_not_called()
    mock_run_entrypoint.assert_called_once_with()
    runner._executor.shutdown.assert_called_once_with(
        wait=True, cancel_futures=True
    )
    monitoring_thread.join.assert_called_once_with()
    startup_thread.join.assert_called_once_with()
    runner._pause_coordinator.unregister.assert_called_once_with(runner)
