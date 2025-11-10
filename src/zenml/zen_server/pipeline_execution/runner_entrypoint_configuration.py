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
"""Runner entrypoint configuration."""

from typing import Any, Dict, List
from uuid import UUID

from zenml.client import Client
from zenml.entrypoints.base_entrypoint_configuration import (
    BaseEntrypointConfiguration,
)
from zenml.execution.pipeline.utils import submit_pipeline

PLACEHOLDER_RUN_ID_OPTION = "placeholder_run_id"


class RunnerEntrypointConfiguration(BaseEntrypointConfiguration):
    """Runner entrypoint configuration."""

    @classmethod
    def get_entrypoint_options(cls) -> Dict[str, bool]:
        """Gets all options required for running with this configuration.

        Returns:
            The superclass options as well as an option for the name of the
            step to run.
        """
        return super().get_entrypoint_options() | {
            PLACEHOLDER_RUN_ID_OPTION: True
        }

    @classmethod
    def get_entrypoint_arguments(
        cls,
        **kwargs: Any,
    ) -> List[str]:
        """Gets all arguments that the entrypoint command should be called with.

        Args:
            **kwargs: Kwargs, must include the placeholder run id.

        Returns:
            The superclass arguments as well as arguments for the placeholder
            run id.
        """
        return super().get_entrypoint_arguments(**kwargs) + [
            f"--{PLACEHOLDER_RUN_ID_OPTION}",
            str(kwargs[PLACEHOLDER_RUN_ID_OPTION]),
        ]

    def run(self) -> None:
        """Run the entrypoint configuration.

        This method runs the pipeline defined by the snapshot given as input
        to the entrypoint configuration.
        """
        snapshot = self.snapshot
        placeholder_run_id = UUID(
            self.entrypoint_args[PLACEHOLDER_RUN_ID_OPTION]
        )
        placeholder_run = Client().get_pipeline_run(placeholder_run_id)

        stack = Client().active_stack
        assert snapshot.stack and stack.id == snapshot.stack.id

        submit_pipeline(
            snapshot=snapshot,
            stack=stack,
            placeholder_run=placeholder_run,
        )
