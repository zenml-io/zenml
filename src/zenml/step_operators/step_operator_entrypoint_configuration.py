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
"""Abstract base class for entrypoint configurations that run a single step."""

from typing import TYPE_CHECKING, Any, List, Set
from uuid import UUID

from zenml.client import Client
from zenml.config.step_run_info import StepRunInfo
from zenml.entrypoints.step_entrypoint_configuration import (
    StepEntrypointConfiguration,
)
from zenml.orchestrators import input_utils, output_utils
from zenml.orchestrators.step_runner import StepRunner

if TYPE_CHECKING:
    from zenml.config.pipeline_deployment import PipelineDeployment
    from zenml.config.step_configurations import Step

STEP_RUN_ID_OPTION = "step_run_id"


class StepOperatorEntrypointConfiguration(StepEntrypointConfiguration):
    """Base class for step operator entrypoint configurations."""

    @classmethod
    def get_entrypoint_options(cls) -> Set[str]:
        """Gets all options required for running with this configuration.

        Returns:
            The superclass options as well as an option for the step run id.
        """
        return super().get_entrypoint_options() | {
            STEP_RUN_ID_OPTION,
        }

    @classmethod
    def get_entrypoint_arguments(
        cls,
        **kwargs: Any,
    ) -> List[str]:
        """Gets all arguments that the entrypoint command should be called with.

        Args:
            **kwargs: Kwargs, must include the step run id.

        Returns:
            The superclass arguments as well as arguments for the step run id.
        """
        return super().get_entrypoint_arguments(**kwargs) + [
            f"--{STEP_RUN_ID_OPTION}",
            kwargs[STEP_RUN_ID_OPTION],
        ]

    def _run_step(
        self,
        step: "Step",
        deployment: "PipelineDeployment",
    ) -> None:
        """Runs a single step.

        Args:
            step: The step to run.
            deployment: The deployment configuration.
        """
        step_run_id = UUID(self.entrypoint_args[STEP_RUN_ID_OPTION])
        step_run = Client().zen_store.get_run_step(step_run_id)
        pipeline_run = Client().get_pipeline_run(step_run.pipeline_run_id)

        step_run_info = StepRunInfo(
            config=step.config,
            pipeline=deployment.pipeline,
            run_name=pipeline_run.name,
            run_id=pipeline_run.id,
            step_run_id=step_run_id,
        )

        stack = Client().active_stack
        input_artifacts, _ = input_utils.resolve_step_inputs(
            step=step, run_id=pipeline_run.id
        )
        output_artifact_uris = output_utils.prepare_output_artifact_uris(
            step_run=step_run, stack=stack, step=step
        )

        step_runner = StepRunner(step=step, stack=stack)
        step_runner.run(
            input_artifacts=input_artifacts,
            output_artifact_uris=output_artifact_uris,
            step_run_info=step_run_info,
        )
