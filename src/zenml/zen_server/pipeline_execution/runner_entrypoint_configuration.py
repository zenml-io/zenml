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
from zenml.constants import is_true_string_value
from zenml.entrypoints.base_entrypoint_configuration import (
    BaseEntrypointConfiguration,
)
from zenml.execution.pipeline.utils import submit_pipeline

PLACEHOLDER_RUN_ID_OPTION = "placeholder_run_id"
RUN_ID_OPTION = "run_id"
RESUME_OPTION = "resume"


class RunnerEntrypointConfiguration(BaseEntrypointConfiguration):
    """Runner entrypoint configuration."""

    @classmethod
    def get_entrypoint_options(cls) -> Dict[str, bool]:
        """Gets all options required for running with this configuration.

        Returns:
            The superclass options as well as options for the run ID and
            whether the run should be resumed.
        """
        return super().get_entrypoint_options() | {
            RUN_ID_OPTION: True,
            RESUME_OPTION: False,
        }

    @classmethod
    def get_entrypoint_arguments(
        cls,
        **kwargs: Any,
    ) -> List[str]:
        """Gets all arguments that the entrypoint command should be called with.

        Args:
            **kwargs: Kwargs, must include the run ID. The optional `resume`
                flag enables the resume path.

        Returns:
            The superclass arguments as well as arguments for the run ID and
            optional resume flag.
        """
        arguments = super().get_entrypoint_arguments(**kwargs) + [
            f"--{RUN_ID_OPTION}",
            str(kwargs[RUN_ID_OPTION]),
            f"--{PLACEHOLDER_RUN_ID_OPTION}",
            str(kwargs[RUN_ID_OPTION]),
        ]
        if RESUME_OPTION in kwargs:
            arguments.extend(
                [f"--{RESUME_OPTION}", str(kwargs[RESUME_OPTION])]
            )
        return arguments

    def run(self) -> None:
        """Run the entrypoint configuration.

        This method runs or resumes the pipeline defined by the configured
        snapshot.
        """
        snapshot = self.snapshot
        run = Client().get_pipeline_run(
            UUID(self.entrypoint_args[RUN_ID_OPTION])
        )

        stack = Client().active_stack
        assert snapshot.stack and stack.id == snapshot.stack.id

        resume = is_true_string_value(self.entrypoint_args.get(RESUME_OPTION))
        if resume:
            stack.orchestrator.restart_run(
                snapshot=snapshot, run=run, stack=stack, force_async=True
            )
        else:
            submit_pipeline(
                snapshot=snapshot,
                stack=stack,
                placeholder_run=run,
            )
