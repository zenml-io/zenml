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

from contextlib import ExitStack as does_not_raise
from uuid import uuid4

import pytest

from zenml.enums import ExecutionStatus, StackComponentType
from zenml.orchestrators.step_launcher import (
    StepLauncher,
    _get_step_operator,
)
from zenml.stack import Stack


def test_step_operator_validation(local_stack, sample_step_operator):
    """Tests that the step operator gets correctly extracted and validated
    from the stack."""

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
