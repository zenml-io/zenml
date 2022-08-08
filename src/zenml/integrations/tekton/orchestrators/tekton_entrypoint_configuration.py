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

from typing import Any, List, Set

from zenml.entrypoints import StepEntrypointConfiguration
from zenml.steps import BaseStep

RUN_NAME_OPTION = "run_name"


class TektonEntrypointConfiguration(StepEntrypointConfiguration):
    """Entrypoint configuration for running steps on tekton."""

    @classmethod
    def get_custom_entrypoint_options(cls) -> Set[str]:
        return {RUN_NAME_OPTION}

    @classmethod
    def get_custom_entrypoint_arguments(
        cls, step: BaseStep, *args: Any, **kwargs: Any
    ) -> List[str]:
        return [
            f"--{RUN_NAME_OPTION}",
            kwargs[RUN_NAME_OPTION],
        ]

    def get_run_name(self, pipeline_name: str) -> str:
        """Returns the Tekton pipeline run name.

        Args:
            pipeline_name: The name of the pipeline.

        Returns:
            The Tekton pipeline run name.
        """
        return self.entrypoint_args[RUN_NAME_OPTION]
