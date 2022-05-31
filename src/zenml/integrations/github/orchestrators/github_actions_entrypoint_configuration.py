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

from typing import Any, List, Set

from zenml.entrypoints import StepEntrypointConfiguration
from zenml.steps import BaseStep

RUN_NAME_OPTION = "run_name"


class GithubActionsEntrypointConfiguration(StepEntrypointConfiguration):
    """Entrypoint configuration for running steps on GitHub Action runners."""

    @classmethod
    def get_custom_entrypoint_options(cls) -> Set[str]:
        """GitHub Actions specific entrypoint options."""
        return {RUN_NAME_OPTION}

    @classmethod
    def get_custom_entrypoint_arguments(
        cls, step: BaseStep, **kwargs: Any
    ) -> List[str]:
        """Adds a run name argument for the entrypoint."""
        # These placeholders in the workflow file will be replaced with
        # concrete values by the GH action runner
        run_name = (
            "${{ github.run_id }}-${{ github.run_number }}-"
            "${{ github.run_attempt }}"
        )
        return [f"--{RUN_NAME_OPTION}", run_name]

    def get_run_name(self, pipeline_name: str) -> str:
        """Returns the pipeline run name."""
        return self.entrypoint_args[RUN_NAME_OPTION]
