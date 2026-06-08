#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
import pytest

from zenml.config.compiler import Compiler
from zenml.config.pipeline_run_configuration import PipelineRunConfiguration
from zenml.exceptions import StackValidationError, StepInterfaceError
from zenml.pipelines.pipeline_decorator import pipeline
from zenml.steps.base_step import BaseStep
from zenml.steps.command_step import CommandStep


def _success_hook() -> None:
    pass


def test_command_step_has_no_inputs_or_outputs():
    """Tests that a command step has no inputs and no outputs."""
    step = CommandStep(command=["echo", "hi"])

    assert step.entrypoint_definition.inputs == {}
    assert step.entrypoint_definition.outputs == {}
    assert step.configuration.command == ["echo", "hi"]


def test_command_step_disables_caching():
    """Tests that caching is forced off for a command step."""
    step = CommandStep(command=["echo", "hi"], enable_cache=True)

    assert step.configuration.enable_cache is False


def test_command_step_with_empty_command_fails():
    """Tests that constructing a command step with an empty command fails."""
    with pytest.raises(StepInterfaceError):
        CommandStep(command=[])


def test_command_step_can_be_loaded_from_source():
    """Tests that command step source loading returns a valid instance."""
    step = BaseStep.load_from_source("zenml.steps.command_step.CommandStep")

    assert isinstance(step, CommandStep)
    assert step.configuration.command == ["zenml-command-step-from-source"]


def test_command_step_subclass_with_inputs_fails():
    """Tests that a command step subclass declaring inputs fails."""

    class _WithInput(CommandStep):
        def entrypoint(self, x: int) -> None:  # type: ignore[override]
            pass

    with pytest.raises(StepInterfaceError):
        _WithInput(command=["echo", "hi"])


def test_command_step_subclass_with_outputs_fails():
    """Tests that a command step subclass declaring outputs fails."""

    class _WithOutput(CommandStep):
        def entrypoint(self) -> int:  # type: ignore[override]
            return 1

    with pytest.raises(StepInterfaceError):
        _WithOutput(command=["echo", "hi"])


def test_command_step_with_hooks_fails():
    """Tests that command steps reject hook configuration."""
    with pytest.raises(StepInterfaceError):
        CommandStep(command=["echo", "hi"], on_success=_success_hook)


def test_command_step_configure_with_hooks_fails():
    """Tests that command steps reject hooks in `configure`."""
    step = CommandStep(command=["echo", "hi"])

    with pytest.raises(StepInterfaceError):
        step.configure(on_success=_success_hook)


def test_pipeline_hooks_on_command_step_fail_compilation(local_stack):
    """Tests that pipeline-level hooks cannot be applied to command steps."""

    @pipeline(dynamic=True, on_success=_success_hook)
    def _pipeline() -> None:
        CommandStep(command=["echo", "hi"])()

    pipeline_instance = _pipeline()
    pipeline_instance.prepare()

    with pytest.raises(StepInterfaceError):
        Compiler().compile(
            pipeline=pipeline_instance,
            stack=local_stack,
            run_configuration=PipelineRunConfiguration(),
        )


def test_command_step_in_static_pipeline_without_step_operator_fails(
    one_step_pipeline, local_stack
):
    """Tests that a command step in a static pipeline without a step operator
    fails to compile."""
    pipeline_instance = one_step_pipeline(CommandStep(command=["echo", "hi"]))
    pipeline_instance.prepare()

    with pytest.raises(StackValidationError):
        Compiler().compile(
            pipeline=pipeline_instance,
            stack=local_stack,
            run_configuration=PipelineRunConfiguration(),
        )
