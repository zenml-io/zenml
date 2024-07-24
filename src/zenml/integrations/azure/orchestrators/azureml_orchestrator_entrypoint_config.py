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
"""Entrypoint configuration for ZenML Sagemaker pipeline steps."""

import json
import os
from typing import Any, List, Set

from zenml.entrypoints.step_entrypoint_configuration import (
    StepEntrypointConfiguration,
)
from zenml.utils.string_utils import b64_decode

ENVIRONMENTAL_VARIABLES = "environmental_variables"
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
        return super().get_entrypoint_options() | {ENVIRONMENTAL_VARIABLES}

    @classmethod
    def get_entrypoint_arguments(
        cls,
        **kwargs: Any,
    ) -> List[str]:
        """Gets all arguments that the entrypoint command should be called with.

        Args:
            **kwargs: Kwargs, can include the environmental variables.

        Returns:
            The superclass arguments as well as arguments for environmental
            variables.
        """
        return super().get_entrypoint_arguments(**kwargs) + [
            f"--{ENVIRONMENTAL_VARIABLES}",
            kwargs[ENVIRONMENTAL_VARIABLES],
        ]

    def _set_env_variables(self):
        env_variables = json.loads(
            b64_decode(self.entrypoint_args[ENVIRONMENTAL_VARIABLES])
        )

        os.environ.update(env_variables)

    def run(self) -> None:
        """Runs the step."""
        self._set_env_variables()

        import os

        os.chdir("/app")

        if completed := os.environ.get(AZURE_ML_OUTPUT_COMPLETED):
            os.makedirs(os.path.dirname(completed), exist_ok=True)
            with open(completed, "w") as f:
                f.write(f"Component completed!")

        # Run the step
        super().run()
