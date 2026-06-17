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
import functools
import subprocess
import sys
from contextlib import ExitStack as does_not_raise

import pytest

from zenml.config.compiler import Compiler
from zenml.config.pipeline_run_configuration import PipelineRunConfiguration
from zenml.constants import CODE_HASH_PARAMETER_NAME
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


def test_command_step_command_affects_code_hash():
    """Tests that the command is part of the code hash caching parameter."""
    step_1 = CommandStep(command=["echo", "hi"])
    step_2 = CommandStep(command=["echo", "bye"])

    assert (
        step_1.caching_parameters[CODE_HASH_PARAMETER_NAME]
        != step_2.caching_parameters[CODE_HASH_PARAMETER_NAME]
    )


def test_command_step_with_empty_command_fails():
    """Tests that constructing a command step with an empty command fails."""
    with pytest.raises(StepInterfaceError):
        CommandStep(command=[])


def test_command_step_entrypoint_runs_command(tmp_path):
    """Tests that the step entrypoint runs the configured command."""
    output_file = tmp_path / "output.txt"
    step = CommandStep(
        command=[sys.executable, "-c", f"open(r'{output_file}', 'w').close()"]
    )

    step.entrypoint()

    assert output_file.exists()


def test_command_step_entrypoint_raises_on_failure():
    """Tests that the step entrypoint raises if the command fails."""
    step = CommandStep(command=[sys.executable, "-c", "raise SystemExit(1)"])

    with pytest.raises(subprocess.CalledProcessError):
        step.entrypoint()


def _self_contained_function() -> None:
    import json

    print(json.dumps({"status": "done"}))


def test_command_step_with_function():
    """Tests that a command step can be constructed from a function."""
    step = CommandStep(command=_self_contained_function)

    command = step.configuration.command
    assert command is not None
    assert command[:2] == ["python", "-c"]
    assert "_self_contained_function()" in command[2]

    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 0
    assert result.stdout.strip() == '{"status": "done"}'


def test_command_step_with_lambda_fails():
    """Tests that lambdas are rejected as command step functions."""
    with pytest.raises(StepInterfaceError):
        CommandStep(command=lambda: None)


def test_command_step_with_function_with_parameters_fails():
    """Tests that functions with parameters are rejected."""

    def _with_parameter(x: int = 1) -> None:
        pass

    with pytest.raises(StepInterfaceError):
        CommandStep(command=_with_parameter)


def test_command_step_with_closure_fails():
    """Tests that closures are rejected as command step functions."""
    captured = "value"

    def _closure() -> None:
        print(captured)

    with pytest.raises(StepInterfaceError):
        CommandStep(command=_closure)


def test_command_step_with_decorated_function_fails():
    """Tests that decorated functions are rejected."""

    def _decorator(func):
        @functools.wraps(func)
        def _wrapper() -> None:
            func()

        return _wrapper

    @_decorator
    def _decorated() -> None:
        pass

    with pytest.raises(StepInterfaceError):
        CommandStep(command=_decorated)


def test_command_step_with_method_fails():
    """Tests that methods are rejected as command step functions."""

    class _WithMethod:
        def method(self) -> None:
            pass

    with pytest.raises(StepInterfaceError):
        CommandStep(command=_WithMethod().method)


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


@pipeline(dynamic=True, on_success=_success_hook)
def _pipeline() -> None:
    CommandStep(command=["echo", "hi"])()


def test_pipeline_hooks_do_not_fail_command_step_compilation(local_stack):
    """Tests that pipeline-level hooks do not fail compilation of command steps."""

    pipeline_instance = _pipeline
    pipeline_instance.prepare()

    with does_not_raise():
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
