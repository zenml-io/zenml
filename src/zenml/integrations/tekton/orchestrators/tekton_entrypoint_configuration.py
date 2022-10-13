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
"""Implementation of the Tekton entrypoint configuration."""

from typing import Any, List, Optional, Set, cast

from zenml.entrypoints import StepEntrypointConfiguration

RUN_NAME_OPTION = "run_name"


class TektonEntrypointConfiguration(StepEntrypointConfiguration):
    """Entrypoint configuration for running steps on Tekton."""

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
        # Tekton replaces the `$(context.pipelineRun.name)` with the actual
        # run name when executing a container. This allows users to re-trigger
        # runs on the Tekton UI and uses the new run name for storing
        # information in the metadata store.
        return super().get_entrypoint_arguments(**kwargs) + [
            f"--{RUN_NAME_OPTION}",
            "$(context.pipelineRun.name)",
        ]

    def get_run_name(self, pipeline_name: str) -> Optional[str]:
        """Returns the pipeline run name.

        Args:
            pipeline_name: The name of the pipeline.

        Returns:
            The pipeline run name passed as argument to the entrypoint.
        """
        return cast(str, self.entrypoint_args[RUN_NAME_OPTION])
