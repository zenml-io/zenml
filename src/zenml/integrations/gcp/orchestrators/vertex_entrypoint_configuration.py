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
"""Implementation of the VertexAI entrypoint configuration."""

from typing import Any, List, Optional, Set

from zenml.entrypoints import StepEntrypointConfiguration

VERTEX_JOB_ID_OPTION = "vertex_job_id"


class VertexEntrypointConfiguration(StepEntrypointConfiguration):
    """Entrypoint configuration for running steps on Vertex AI Pipelines."""

    @classmethod
    def get_entrypoint_options(cls) -> Set[str]:
        """Gets all options required for running with this configuration.

        Returns:
            The superclass options as well as an option for the Vertex job id.
        """
        return super().get_entrypoint_options() | {VERTEX_JOB_ID_OPTION}

    @classmethod
    def get_entrypoint_arguments(
        cls,
        **kwargs: Any,
    ) -> List[str]:
        """Gets all arguments that the entrypoint command should be called with.

        Args:
            **kwargs: Kwargs, must include the Vertex job id.

        Returns:
            The superclass arguments as well as arguments for the Vertex job id.
        """
        return super().get_entrypoint_arguments(**kwargs) + [
            f"--{VERTEX_JOB_ID_OPTION}",
            kwargs[VERTEX_JOB_ID_OPTION],
        ]

    def get_run_name(self, pipeline_name: str) -> Optional[str]:
        """Returns the Vertex AI Pipeline job id.

        Args:
            pipeline_name: The name of the pipeline.

        Returns:
            The Vertex AI Pipeline job id.
        """
        job_id: str = self.entrypoint_args[VERTEX_JOB_ID_OPTION]
        return job_id
