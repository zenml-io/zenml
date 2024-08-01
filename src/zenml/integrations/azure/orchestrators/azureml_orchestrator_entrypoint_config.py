#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Entrypoint configuration for ZenML AzureML pipeline steps."""

import json
import os
from typing import Any, List, Set

from zenml.entrypoints.step_entrypoint_configuration import (
    StepEntrypointConfiguration,
)
from zenml.utils.string_utils import b64_decode

ZENML_ENV_VARIABLES = "zenml_env_variables"
AZURE_ML_OUTPUT_COMPLETED = "AZURE_ML_OUTPUT_COMPLETED"


class AzureMLEntrypointConfiguration(StepEntrypointConfiguration):
    """Entrypoint configuration for ZenML AzureML pipeline steps."""

    @classmethod
    def get_entrypoint_options(cls) -> Set[str]:
        """Gets all options required for running with this configuration.

        Returns:
            The superclass options as well as an option for the
            environmental variables.
        """
        return super().get_entrypoint_options() | {ZENML_ENV_VARIABLES}

    @classmethod
    def get_entrypoint_arguments(cls, **kwargs: Any) -> List[str]:
        """Gets all arguments that the entrypoint command should be called with.

        Args:
            **kwargs: Kwargs, can include the environmental variables.

        Returns:
            The superclass arguments as well as arguments for environmental
            variables.
        """
        return super().get_entrypoint_arguments(**kwargs) + [
            f"--{ZENML_ENV_VARIABLES}",
            kwargs[ZENML_ENV_VARIABLES],
        ]

    def _set_env_variables(self) -> None:
        """Sets the environmental variables before executing the step."""
        env_variables = json.loads(
            b64_decode(self.entrypoint_args[ZENML_ENV_VARIABLES])
        )
        os.environ.update(env_variables)

    def run(self) -> None:
        """Runs the step."""
        # Set the environmental variables first
        self._set_env_variables()

        # Azure automatically changes the working directory, we have to set it
        # back to /app before running the step.
        os.chdir("/app")

        # Run the step
        super().run()

        # Unfortunately, in AzureML's Python SDK v2, there is no native way
        # to execute steps/components in a specific sequence. In order to
        # establish the correct order, we are using dummy inputs and
        # outputs. However, these steps only execute if the inputs and outputs
        # actually exist. This is why we create a dummy file and write to it and
        # use it as the output of the steps.
        if completed := os.environ.get(AZURE_ML_OUTPUT_COMPLETED):
            os.makedirs(os.path.dirname(completed), exist_ok=True)
            with open(completed, "w") as f:
                f.write("Component completed!")
