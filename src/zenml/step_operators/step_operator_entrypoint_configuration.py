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
    STEP_NAME_OPTION,
    StepEntrypointConfiguration,
)
from zenml.orchestrators.launcher import (
    Launcher,
    prepare_input_artifacts,
    prepare_output_artifacts,
)
from zenml.steps.utils import StepExecutor

if TYPE_CHECKING:
    from zenml.config.pipeline_deployment import PipelineDeployment
    from zenml.config.step_configurations import Step

PIPELINE_RUN_ID_OPTION = "pipeline_run_id"
STEP_RUN_ID_OPTION = "step_run_id"


class StepOperatorEntrypointConfiguration(StepEntrypointConfiguration):
    """Base class for step operator entrypoint configurations."""

    @classmethod
    def get_entrypoint_options(cls) -> Set[str]:
        """Gets all options required for running with this configuration.

        Returns:
            The superclass options as well as an option for the path to the
            execution info.
        """
        return super().get_entrypoint_options() | {
            PIPELINE_RUN_ID_OPTION,
            STEP_RUN_ID_OPTION,
        }

    @classmethod
    def get_entrypoint_arguments(
        cls,
        **kwargs: Any,
    ) -> List[str]:
        """Gets all arguments that the entrypoint command should be called with.

        Args:
            **kwargs: Kwargs, must include the execution info path.

        Returns:
            The superclass arguments as well as arguments for the path to the
            execution info.
        """
        return super().get_entrypoint_arguments(**kwargs) + [
            f"--{PIPELINE_RUN_ID_OPTION}",
            kwargs[PIPELINE_RUN_ID_OPTION],
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
        # Make sure the artifact store is loaded before we load the execution
        # info
        stack = Client().active_stack

        step_name = self.entrypoint_args[STEP_NAME_OPTION]
        pipeline_run_id = self.entrypoint_args[PIPELINE_RUN_ID_OPTION]
        step_run_id = self.entrypoint_args[STEP_RUN_ID_OPTION]

        pipeline_run = Client().zen_store.get_run(
            run_name_or_id=UUID(pipeline_run_id)
        )
        step_run = Client().zen_store.get_run_step(
            step_run_id=UUID(step_run_id)
        )

        step_run_info = StepRunInfo(
            config=step.config,
            pipeline=deployment.pipeline,
            run_name=pipeline_run.name,
        )

        launcher = Launcher(
            step=step,
            step_name=step_name,
            run_name=pipeline_run.name,
            pipeline_config=deployment.pipeline,
            stack=stack,
        )
        input_artifact_ids, _ = launcher._resolve_inputs(run_id=pipeline_run.id)

        input_artifacts = prepare_input_artifacts(
            input_artifact_ids=input_artifact_ids
        )
        output_artifacts = prepare_output_artifacts(
            step_run=step_run, stack=stack, step=step
        )

        executor = StepExecutor(step=step, step_run=step_run)

        stack.prepare_step_run(info=step_run_info)
        try:
            executor.execute(
                input_artifacts=input_artifacts,
                output_artifacts=output_artifacts,
                run_name=pipeline_run.name,
                pipeline_config=deployment.pipeline,
            )
        finally:
            stack.cleanup_step_run(info=step_run_info)
