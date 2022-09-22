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
"""Entrypoint configuration for the Kubernetes worker/step pods."""

from typing import Any, List, Optional, Set

from zenml.entrypoints import StepEntrypointConfiguration

RUN_NAME_OPTION = "run_name"


class KubernetesStepEntrypointConfiguration(StepEntrypointConfiguration):
    """Entrypoint configuration for running steps on Kubernetes."""

    @classmethod
    def get_entrypoint_options(cls) -> Set[str]:
        """Gets all options required for running with this configuration.

        Returns:
            The superclass options as well as an option for the run name.
        """
        return super().get_entrypoint_options() | {RUN_NAME_OPTION}

    @classmethod
    def get_entrypoint_arguments(cls, **kwargs: Any) -> List[str]:
        """Gets all arguments that the entrypoint command should be called with.

        Args:
            **kwargs: Kwargs, must include the run name.

        Returns:
            The superclass arguments as well as arguments for the run name.
        """
        return super().get_entrypoint_arguments(**kwargs) + [
            f"--{RUN_NAME_OPTION}",
            kwargs[RUN_NAME_OPTION],
        ]

    def get_run_name(self, pipeline_name: str) -> Optional[str]:
        """Returns the ZenML run name.

        Args:
            pipeline_name: Name of the ZenML pipeline (unused).

        Returns:
            ZenML run name.
        """
        job_id: str = self.entrypoint_args[RUN_NAME_OPTION]
        return job_id
