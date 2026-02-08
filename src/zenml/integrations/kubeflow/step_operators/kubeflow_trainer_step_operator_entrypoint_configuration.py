#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""Entrypoint configuration for Kubeflow Trainer step operator."""

from typing import TYPE_CHECKING

from zenml.client import Client
from zenml.config.step_configurations import Step
from zenml.config.step_run_info import StepRunInfo
from zenml.integrations.kubeflow.step_operators.distributed_utils import (
    is_primary_distributed_replica,
    normalize_kubeflow_trainer_distributed_env,
)
from zenml.integrations.kubeflow.step_operators.kubeflow_trainer_step_runner import (
    KubeflowTrainerStepRunner,
)
from zenml.orchestrators import input_utils, output_utils
from zenml.step_operators.step_operator_entrypoint_configuration import (
    STEP_NAME_OPTION,
    StepOperatorEntrypointConfiguration,
)

if TYPE_CHECKING:
    from zenml.models import PipelineSnapshotResponse


class KubeflowTrainerStepOperatorEntrypointConfiguration(
    StepOperatorEntrypointConfiguration
):
    """Entry point config that uses distributed-aware step execution."""

    def _run_step(
        self,
        step: Step,
        snapshot: "PipelineSnapshotResponse",
    ) -> None:
        """Runs a single step using the Kubeflow Trainer step runner.

        Args:
            step: The step to run.
            snapshot: The snapshot configuration.
        """
        normalize_kubeflow_trainer_distributed_env()

        step_run = self.step_run
        pipeline_run = Client().get_pipeline_run(step_run.pipeline_run_id)

        step_run_info = StepRunInfo(
            config=step.config,
            spec=step.spec,
            snapshot=snapshot,
            pipeline=snapshot.pipeline_configuration,
            run_name=pipeline_run.name,
            pipeline_step_name=self.entrypoint_args[STEP_NAME_OPTION],
            run_id=pipeline_run.id,
            step_run_id=step_run.id,
            force_write_logs=lambda: None,
        )

        stack = Client().active_stack

        input_utils.resolve_step_inputs(step=step, pipeline_run=pipeline_run)

        output_artifact_uris = output_utils.prepare_output_artifact_uris(
            step_run=step_run,
            stack=stack,
            step=step,
            skip_artifact_materialization=not is_primary_distributed_replica(),
        )

        step_runner = KubeflowTrainerStepRunner(step=step, stack=stack)
        step_runner.run(
            pipeline_run=pipeline_run,
            step_run=step_run,
            input_artifacts=step_run.inputs,
            output_artifact_uris=output_artifact_uris,
            step_run_info=step_run_info,
        )
