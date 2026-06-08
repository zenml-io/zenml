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
"""Step that runs an opaque container command."""

from typing import TYPE_CHECKING, Any, Dict, List

from zenml.exceptions import StepInterfaceError
from zenml.steps.base_step import BaseStep

if TYPE_CHECKING:
    from zenml.config.step_configurations import StepConfigurationUpdate


class CommandStep(BaseStep):
    """Step that runs an opaque container command."""

    def __init__(self, command: List[str], **kwargs: Any) -> None:
        """Initializes a command step.

        Args:
            command: The command to run for the step.
            **kwargs: Keyword arguments to configure the step. Forwarded to
                the `BaseStep` constructor.

        Raises:
            StepInterfaceError: If the command is empty, or if a subclass
                overrides the entrypoint to declare inputs or outputs.
        """
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

    def entrypoint(self) -> None:
        """No-op entrypoint. A command step has no Python body to run."""

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

        if config.failure_hook_source or config.success_hook_source:
            raise StepInterfaceError(
                "Command steps do not support success or failure hooks."
            )
