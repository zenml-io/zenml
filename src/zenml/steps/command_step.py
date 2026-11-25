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
"""Step that runs an opaque container command."""

import inspect
import subprocess
import textwrap
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Union

from zenml.exceptions import StepInterfaceError
from zenml.steps.base_step import BaseStep

if TYPE_CHECKING:
    from zenml.config.step_configurations import StepConfigurationUpdate


def _build_function_command(func: Callable[[], Any]) -> List[str]:
    """Builds a command that runs a function using `python -c`.

    Args:
        func: The function to run.

    Raises:
        StepInterfaceError: If the function is not a plain undecorated
            function without parameters, or if its source code cannot be
            extracted.

    Returns:
        The command.
    """
    if not inspect.isfunction(func):
        raise StepInterfaceError(
            "The object passed as command step function is not a function: "
            f"`{func}`."
        )

    if func.__name__ == "<lambda>":
        raise StepInterfaceError(
            "Lambdas cannot be used as command step functions."
        )

    if hasattr(func, "__wrapped__"):
        raise StepInterfaceError(
            f"The command step function `{func.__name__}` cannot be decorated."
        )

    if func.__closure__ is not None:
        raise StepInterfaceError(
            f"The command step function `{func.__name__}` cannot reference "
            "variables from an enclosing function."
        )

    if inspect.signature(func).parameters:
        raise StepInterfaceError(
            f"The command step function `{func.__name__}` cannot have "
            "parameters."
        )

    try:
        source = textwrap.dedent(inspect.getsource(func))
    except (OSError, TypeError):
        raise StepInterfaceError(
            "Failed to get the source code of the command step function "
            f"`{func.__name__}`."
        )

    if source.lstrip().startswith("@"):
        raise StepInterfaceError(
            f"The command step function `{func.__name__}` cannot be decorated."
        )

    code = f"{source}\n{func.__name__}()\n"

    try:
        compile(code, "<command-step>", "exec")
    except SyntaxError as e:
        raise StepInterfaceError(
            "Failed to compile the source code of the command step function "
            f"`{func.__name__}`: {e}"
        )

    return ["python", "-c", code]


class CommandStep(BaseStep):
    """Step that runs an opaque container command."""

    def __init__(
        self,
        command: Union[List[str], Callable[[], Any]],
        **kwargs: Any,
    ) -> None:
        """Initializes a command step.

        Args:
            command: The command to run for the step, or a self-contained
                function to run with `python -c`.
            **kwargs: Keyword arguments to configure the step. Forwarded to
                the `BaseStep` constructor.

        Raises:
            StepInterfaceError: If the command is empty, or if a subclass
                overrides the entrypoint to declare inputs or outputs.
        """
        if callable(command):
            command = _build_function_command(command)

        if not command:
            raise StepInterfaceError(
                "The command of a command step must not be empty."
            )

        super().__init__(**kwargs)

        if (
            self.entrypoint_definition.inputs
            or self.entrypoint_definition.outputs
        ):
            raise StepInterfaceError(
                "A command step cannot have inputs or outputs. Do not override "
                "the `entrypoint` method with parameters or a return annotation."
            )

        self._configuration = self._configuration.model_copy(
            update={"command": command, "enable_cache": False}
        )

    @classmethod
    def _load_from_source(cls) -> "BaseStep":
        """Creates a command step instance from a source class.

        Returns:
            A command step instance.
        """
        # When being loaded from source, we do not yet have access to the
        # configuration. So we just return a step with a dummy command.
        return cls(command=["zenml-command-step-from-source"])

    @property
    def source_code_cache_value(self) -> str:
        """The source code cache value of this step.

        Returns:
            The source code cache value of this step.
        """
        # This value is captured at compile time on the original step
        # instance, so the dummy command of instances loaded from source
        # never ends up in it.
        command = self.configuration.command
        assert command is not None
        return self.source_code + str(command)

    def entrypoint(self) -> None:
        """Runs the configured command as a subprocess."""
        command = self.configuration.command
        assert command is not None
        subprocess.run(command, check=True)

    def _validate_configuration(
        self,
        config: "StepConfigurationUpdate",
        runtime_parameters: Dict[str, Any],
    ) -> None:
        """Validates command step configuration updates.

        Args:
            config: The configuration update to validate.
            runtime_parameters: Runtime parameters passed to the step.

        Raises:
            StepInterfaceError: If success or failure hooks are configured.
        """
        super()._validate_configuration(
            config=config, runtime_parameters=runtime_parameters
        )

        if (
            config.failure_hook_source
            or config.success_hook_source
            or config.end_hook_source
            or config.start_hook_source
        ):
            raise StepInterfaceError("Command steps do not support hooks.")
