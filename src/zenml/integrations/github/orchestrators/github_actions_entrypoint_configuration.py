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
"""Implementation of the GitHub Actions Orchestrator entrypoint."""

from typing import Any, List, Optional, Set, cast

from zenml.entrypoints import StepEntrypointConfiguration

RUN_ID_OPTION = "run_id"


class GitHubActionsEntrypointConfiguration(StepEntrypointConfiguration):
    """Entrypoint configuration for running steps on GitHub Actions runners."""

    @classmethod
    def get_entrypoint_options(cls) -> Set[str]:
        """GitHub Actions specific entrypoint options.

        Returns:
            Set with the custom run id option.
        """
        return super().get_entrypoint_options() | {RUN_ID_OPTION}

    @classmethod
    def get_entrypoint_arguments(cls, **kwargs: Any) -> List[str]:
        """Adds a run id argument for the entrypoint.

        Args:
            **kwargs: Additional args.

        Returns:
            GitHub Actions placeholder for the run id option.
        """
        # These placeholders in the workflow file will be replaced with
        # concrete values by the GitHub Actions runner
        run_id = (
            "${{ github.run_id }}_${{ github.run_number }}_"
            "${{ github.run_attempt }}"
        )
        return super().get_entrypoint_arguments(**kwargs) + [
            f"--{RUN_ID_OPTION}",
            run_id,
        ]

    def get_run_name(self, pipeline_name: str) -> Optional[str]:
        """Returns the pipeline run name.

        Args:
            pipeline_name: Name of the pipeline which will run.

        Returns:
            The run name.
        """
        run_id = cast(str, self.entrypoint_args[RUN_ID_OPTION])
        return f"{pipeline_name}-{run_id}"
