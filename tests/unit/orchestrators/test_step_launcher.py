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
"""Unit tests for step launcher routing and validation."""

from contextlib import ExitStack as does_not_raise
from typing import Any, Dict
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from zenml.config.pipeline_configurations import PipelineConfiguration
from zenml.config.step_configurations import Step
from zenml.config.step_run_info import StepRunInfo
from zenml.enums import StackComponentType
from zenml.models import (
    PipelineRunResponse,
    PipelineSnapshotResponse,
    StepRunResponse,
)
from zenml.orchestrators.step_launcher import (
    StepLauncher,
    _get_step_operator,
)
from zenml.stack import Stack
from zenml.zenbabel.adapters import PORTABLE_STEP_ADAPTER_SOURCE


def test_step_operator_validation(local_stack, sample_step_operator):
    """Tests that the step operator gets correctly extracted and validated.

    from the stack.
    """
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


def _launcher(
    step: Step, local_stack: Stack, is_dynamic: bool = False
) -> StepLauncher:
    launcher = StepLauncher.__new__(StepLauncher)
    launcher._step = step
    launcher._stack = local_stack
    launcher._invocation_id = step.spec.invocation_id
    launcher._snapshot = MagicMock(
        is_dynamic=is_dynamic,
        pipeline_configuration=PipelineConfiguration(name="pipeline_name"),
    )
    return launcher


def _python_step(execution_spec: Dict[str, Any] | None = None) -> Step:
    spec: Dict[str, Any] = {
        "source": "tests.unit.orchestrators.test_step_runner.successful_step",
        "upstream_steps": [],
        "invocation_id": "python_step",
    }
    if execution_spec:
        spec["execution_spec"] = execution_spec

    return Step.model_validate(
        {
            "spec": spec,
            "config": {"name": "python_step"},
        }
    )


def _portable_step() -> Step:
    return Step.model_validate(
        {
            "spec": {
                "source": PORTABLE_STEP_ADAPTER_SOURCE,
                "upstream_steps": [],
                "invocation_id": "portable_step",
                "execution_spec": {
                    "language": "typescript",
                    "protocol": "zenml-portable-json-v1",
                    "command": ["node", "/app/dist/step.js"],
                    "source_identity": "ts/src/step.ts#step",
                },
            },
            "config": {"name": "portable_step"},
        }
    )


def test_current_thread_routing_keeps_python_steps_on_step_runner(
    mocker: Any,
    local_stack: Stack,
    sample_pipeline_run: PipelineRunResponse,
    sample_step_run: StepRunResponse,
) -> None:
    """Python/default steps keep the existing StepRunner route."""
    step = _python_step()
    launcher = _launcher(step, local_stack)
    step_runner = mocker.patch("zenml.orchestrators.step_launcher.StepRunner")
    portable_runner = mocker.patch(
        "zenml.orchestrators.step_launcher.PortableStepRunner"
    )

    launcher._run_step_in_current_thread(
        pipeline_run=sample_pipeline_run,
        step_run=sample_step_run,
        step_run_info=MagicMock(spec=StepRunInfo),
        input_artifacts={},
        output_artifact_uris={},
    )

    step_runner.assert_called_once_with(step=step, stack=local_stack)
    step_runner.return_value.run.assert_called_once()
    portable_runner.assert_not_called()


def test_current_thread_routing_keeps_explicit_python_protocol_on_step_runner(
    mocker: Any,
    local_stack: Stack,
    sample_pipeline_run: PipelineRunResponse,
    sample_step_run: StepRunResponse,
) -> None:
    """Explicit Python execution specs keep the existing StepRunner route."""
    step = _python_step(
        execution_spec={
            "language": "python",
            "protocol": "zenml-python-step-v1",
            "command": ["python", "-m", "zenml.entrypoints.entrypoint"],
            "source_identity": "tests/python_step.py#python_step",
        }
    )
    launcher = _launcher(step, local_stack)
    step_runner = mocker.patch("zenml.orchestrators.step_launcher.StepRunner")
    portable_runner = mocker.patch(
        "zenml.orchestrators.step_launcher.PortableStepRunner"
    )

    launcher._run_step_in_current_thread(
        pipeline_run=sample_pipeline_run,
        step_run=sample_step_run,
        step_run_info=MagicMock(spec=StepRunInfo),
        input_artifacts={},
        output_artifact_uris={},
    )

    step_runner.assert_called_once_with(step=step, stack=local_stack)
    step_runner.return_value.run.assert_called_once()
    portable_runner.assert_not_called()


def test_current_thread_routing_sends_portable_steps_to_portable_runner(
    mocker: Any,
    local_stack: Stack,
    sample_pipeline_run: PipelineRunResponse,
    sample_step_run: StepRunResponse,
) -> None:
    """Portable JSON steps use the dedicated portable runner."""
    step = _portable_step()
    launcher = _launcher(step, local_stack)
    step_runner = mocker.patch("zenml.orchestrators.step_launcher.StepRunner")
    portable_runner = mocker.patch(
        "zenml.orchestrators.step_launcher.PortableStepRunner"
    )

    launcher._run_step_in_current_thread(
        pipeline_run=sample_pipeline_run,
        step_run=sample_step_run,
        step_run_info=MagicMock(spec=StepRunInfo),
        input_artifacts={},
        output_artifact_uris={},
    )

    portable_runner.assert_called_once_with(step=step, stack=local_stack)
    portable_runner.return_value.run.assert_called_once()
    step_runner.assert_not_called()


def test_dynamic_portable_steps_are_rejected_before_execution(
    mocker: Any,
    local_stack: Stack,
    sample_pipeline_run: PipelineRunResponse,
    sample_step_run: StepRunResponse,
    sample_snapshot_response_model: PipelineSnapshotResponse,
) -> None:
    """Portable steps are a static-pipeline-only v1 feature."""
    step = _portable_step()
    launcher = _launcher(step, local_stack, is_dynamic=True)
    launcher._snapshot = sample_snapshot_response_model.model_copy(
        update={
            "body": sample_snapshot_response_model.body.model_copy(
                update={"is_dynamic": True}
            )
        }
    )
    mocker.patch(
        "zenml.orchestrators.step_launcher.output_utils.prepare_output_artifact_uris",
        return_value={},
    )
    mocker.patch.object(StepLauncher, "_wait_until_resources_acquired")
    current_thread = mocker.patch.object(
        StepLauncher, "_run_step_in_current_thread"
    )

    with pytest.raises(RuntimeError, match="static pipelines in v1"):
        launcher._run_step(
            pipeline_run=sample_pipeline_run,
            step_run=sample_step_run,
            force_write_logs=lambda: None,
        )

    current_thread.assert_not_called()
