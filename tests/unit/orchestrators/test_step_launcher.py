#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""Tests for step launcher helpers."""

from contextlib import ExitStack as does_not_raise
from types import SimpleNamespace
from uuid import uuid4

import pytest

from zenml.enums import ExecutionStatus, StackComponentType, StepRuntime
from zenml.orchestrators.step_launcher import (
    StepLauncher,
    _get_step_operator,
)
from zenml.stack import Stack


def _dynamic_launcher(step_operator=None) -> StepLauncher:
    """Create a minimal launcher for dynamic runtime checks."""
    launcher = object.__new__(StepLauncher)
    launcher._snapshot = SimpleNamespace(
        is_dynamic=True,
        pipeline_configuration=SimpleNamespace(docker_settings=None),
    )
    launcher._step = SimpleNamespace(
        config=SimpleNamespace(step_operator=step_operator)
    )
    launcher._stack = SimpleNamespace(orchestrator=object())
    return launcher


def test_dynamic_orchestrator_detection_requires_isolated_runtime(
    monkeypatch,
) -> None:
    """Tests that only dynamic isolated orchestrator steps are detected."""
    monkeypatch.setattr(
        "zenml.execution.pipeline.dynamic.compilation.get_step_runtime",
        lambda **_: StepRuntime.ISOLATED,
    )

    assert _dynamic_launcher()._runs_with_dynamic_orchestrator()
    assert not _dynamic_launcher(
        step_operator="operator"
    )._runs_with_dynamic_orchestrator()

    monkeypatch.setattr(
        "zenml.execution.pipeline.dynamic.compilation.get_step_runtime",
        lambda **_: StepRuntime.INLINE,
    )

    assert not _dynamic_launcher()._runs_with_dynamic_orchestrator()


def test_step_operator_validation(local_stack, sample_step_operator):
    """Tests that the step operator gets correctly extracted and validated."""
    with pytest.raises(RuntimeError):
        _get_step_operator(
            stack=local_stack, step_operator_name="step_operator"
        )

    components = local_stack._components
    components[StackComponentType.STEP_OPERATOR] = [sample_step_operator]
    stack_with_step_operator = Stack.from_components_v2(
        id=uuid4(), name="", components=components
    )
    with pytest.raises(RuntimeError):
        _get_step_operator(
            stack=stack_with_step_operator,
            step_operator_name="not_the_step_operator_name",
        )

    with does_not_raise():
        _get_step_operator(
            stack=stack_with_step_operator,
            step_operator_name=sample_step_operator.name,
        )


def test_dynamic_command_step_success_publishes_status(mocker):
    """Test that successful dynamic command steps publish a success status."""
    launcher = object.__new__(StepLauncher)
    launcher._stack = mocker.Mock()
    launcher._stack.orchestrator.wait_for_isolated_step.return_value = (
        ExecutionStatus.COMPLETED
    )
    launcher._wait = True
    launcher._step = mocker.Mock()
    launcher._step.config.command = ["echo", "hi"]

    step_run_info = mocker.Mock()
    step_run_info.step_run = mocker.Mock()
    step_run_info.step_run_id = uuid4()

    mocker.patch(
        "zenml.orchestrators.step_launcher.orchestrator_utils.get_config_environment_vars",
        return_value=({}, {}),
    )
    mocker.patch(
        "zenml.orchestrators.step_launcher.env_utils.get_runtime_environment",
        return_value={},
    )

    publish_success = mocker.patch(
        "zenml.orchestrators.step_launcher.publish_utils.publish_successful_step_run"
    )
    publish_failed = mocker.patch(
        "zenml.orchestrators.step_launcher.publish_utils.publish_failed_step_run"
    )

    launcher._run_step_with_dynamic_orchestrator(step_run_info=step_run_info)

    publish_success.assert_called_once_with(
        step_run_id=step_run_info.step_run_id,
        output_artifact_ids={},
    )
    publish_failed.assert_not_called()


def test_dynamic_command_step_failure_raises(mocker):
    """Test that failed dynamic command steps raise the remote exception."""
    launcher = object.__new__(StepLauncher)
    launcher._stack = mocker.Mock()
    launcher._stack.orchestrator.wait_for_isolated_step.return_value = (
        ExecutionStatus.FAILED
    )
    launcher._wait = True
    launcher._step = mocker.Mock()
    launcher._step.config.command = ["echo", "hi"]

    step_run_info = mocker.Mock()
    step_run_info.step_run = mocker.Mock()
    step_run_info.step_run_id = uuid4()
    step_run_info.pipeline_step_name = "step_name"

    mocker.patch(
        "zenml.orchestrators.step_launcher.orchestrator_utils.get_config_environment_vars",
        return_value=({}, {}),
    )
    mocker.patch(
        "zenml.orchestrators.step_launcher.env_utils.get_runtime_environment",
        return_value={},
    )

    publish_success = mocker.patch(
        "zenml.orchestrators.step_launcher.publish_utils.publish_successful_step_run"
    )
    publish_failed = mocker.patch(
        "zenml.orchestrators.step_launcher.publish_utils.publish_failed_step_run"
    )
    mocker.patch("zenml.orchestrators.step_launcher.Client.get_run_step")
    mocker.patch(
        "zenml.orchestrators.step_launcher.exception_utils.reconstruct_exception",
        return_value=RuntimeError("step failed"),
    )

    with pytest.raises(RuntimeError, match="step failed"):
        launcher._run_step_with_dynamic_orchestrator(
            step_run_info=step_run_info
        )

    publish_success.assert_not_called()
    # Publishing the failed status is the responsibility of the generic
    # exception handling in `StepLauncher.launch(...)`.
    publish_failed.assert_not_called()


def _make_isolated_step_launcher(mocker, status):
    launcher = object.__new__(StepLauncher)
    launcher._stack = mocker.Mock()
    launcher._stack.orchestrator.wait_for_isolated_step.return_value = status
    launcher._wait = True
    launcher._invocation_id = "step_name"
    launcher._step = mocker.Mock()
    launcher._step.config.command = None
    launcher._step.config.step_operator = None

    mocker.patch(
        "zenml.orchestrators.step_launcher.orchestrator_utils.get_config_environment_vars",
        return_value=({}, {}),
    )
    mocker.patch(
        "zenml.orchestrators.step_launcher.env_utils.get_runtime_environment",
        return_value={},
    )
    return launcher


def test_isolated_step_cleanup_called_on_success(mocker):
    """Test that isolated step cleanup runs after successful remote steps."""
    launcher = _make_isolated_step_launcher(mocker, ExecutionStatus.COMPLETED)
    step_run_info = mocker.Mock()

    launcher._run_step_with_dynamic_orchestrator(step_run_info=step_run_info)

    launcher._stack.orchestrator.cleanup_isolated_step.assert_called_once_with(
        step_run_info.step_run
    )


def test_isolated_step_cleanup_called_on_failure(mocker):
    """Test that isolated step cleanup runs after failed remote steps."""
    launcher = _make_isolated_step_launcher(mocker, ExecutionStatus.FAILED)
    step_run_info = mocker.Mock()
    step_run_info.pipeline_step_name = "step_name"

    mocker.patch("zenml.orchestrators.step_launcher.Client.get_run_step")
    mocker.patch(
        "zenml.orchestrators.step_launcher.exception_utils.reconstruct_exception",
        return_value=RuntimeError("step failed"),
    )

    with pytest.raises(RuntimeError, match="step failed"):
        launcher._run_step_with_dynamic_orchestrator(
            step_run_info=step_run_info
        )

    launcher._stack.orchestrator.cleanup_isolated_step.assert_called_once_with(
        step_run_info.step_run
    )


def test_isolated_step_cleanup_skipped_when_not_waiting(mocker):
    """Test that isolated step cleanup is skipped for asynchronous runs."""
    launcher = _make_isolated_step_launcher(mocker, ExecutionStatus.COMPLETED)
    launcher._wait = False
    step_run_info = mocker.Mock()

    launcher._run_step_with_dynamic_orchestrator(step_run_info=step_run_info)

    launcher._stack.orchestrator.wait_for_isolated_step.assert_not_called()
    launcher._stack.orchestrator.cleanup_isolated_step.assert_not_called()


def test_cleanup_remote_step_dispatches_to_step_operator(mocker):
    """Test that remote step cleanup dispatches to the selected operator."""
    launcher = object.__new__(StepLauncher)
    launcher._stack = mocker.Mock()
    launcher._invocation_id = "step_name"
    launcher._step = mocker.Mock()
    launcher._step.config.step_operator = "my_operator"

    step_operator = mocker.Mock()
    get_step_operator = mocker.patch(
        "zenml.orchestrators.step_launcher._get_step_operator",
        return_value=step_operator,
    )
    step_run = mocker.Mock()

    launcher._cleanup_remote_step(step_run)

    get_step_operator.assert_called_once_with(
        stack=launcher._stack, step_operator_name="my_operator"
    )
    step_operator.cleanup_step_submission.assert_called_once_with(step_run)
    launcher._stack.orchestrator.cleanup_isolated_step.assert_not_called()


def test_cleanup_remote_step_swallows_errors(mocker):
    """Test that remote cleanup errors are logged and swallowed."""
    launcher = object.__new__(StepLauncher)
    launcher._stack = mocker.Mock()
    launcher._invocation_id = "step_name"
    launcher._step = mocker.Mock()
    launcher._step.config.step_operator = None
    launcher._stack.orchestrator.cleanup_isolated_step.side_effect = (
        RuntimeError("cleanup boom")
    )

    with does_not_raise():
        launcher._cleanup_remote_step(mocker.Mock())
