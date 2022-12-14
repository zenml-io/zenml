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
"""Implementation of the SageMaker orchestrator."""

import os
from datetime import datetime
from typing import TYPE_CHECKING, Any, cast

import sagemaker
from sagemaker.workflow.pipeline import Pipeline
from sagemaker.workflow.steps import ProcessingStep

from zenml.constants import ORCHESTRATOR_DOCKER_IMAGE_KEY
from zenml.entrypoints import StepEntrypointConfiguration
from zenml.integrations.aws.flavors.sagemaker_orchestrator_flavor import (
    SagemakerOrchestratorConfig,
)
from zenml.orchestrators.base_orchestrator import BaseOrchestrator
from zenml.orchestrators.utils import get_orchestrator_run_name
from zenml.utils.pipeline_docker_image_builder import PipelineDockerImageBuilder

if TYPE_CHECKING:
    from zenml.config.pipeline_deployment import PipelineDeployment
    from zenml.stack import Stack

ENV_ZENML_SAGEMAKER_RUN_ID = "ZENML_SAGEMAKER_RUN_ID"


class SagemakerOrchestrator(BaseOrchestrator):
    """Orchestrator responsible for running pipelines on Sagemaker."""

    @property
    def config(self) -> SagemakerOrchestratorConfig:
        """Returns the `SagemakerOrchestratorConfig` config.

        Returns:
            The configuration.
        """
        return cast(SagemakerOrchestratorConfig, self._config)

    def get_orchestrator_run_id(self) -> str:
        """Returns the run id of the active orchestrator run.

        Important: This needs to be a unique ID and return the same value for
        all steps of a pipeline run.

        Returns:
            The orchestrator run id.
        """
        print(os.environ)
        try:
            return os.environ[ENV_ZENML_SAGEMAKER_RUN_ID]
        except KeyError:
            raise RuntimeError(
                "Unable to read run id from environment variable "
                f"{ENV_ZENML_SAGEMAKER_RUN_ID}."
            )

    def prepare_pipeline_deployment(
        self, deployment: "PipelineDeployment", stack: "Stack"
    ) -> None:
        """Build a Docker image and push it to the container registry.

        Args:
            deployment: The pipeline deployment configuration.
            stack: The stack on which the pipeline will be deployed.
        """
        docker_image_builder = PipelineDockerImageBuilder()
        repo_digest = docker_image_builder.build_and_push_docker_image(
            deployment=deployment, stack=stack
        )
        # repo_digest = "715803424590.dkr.ecr.eu-north-1.amazonaws.com/zenml:not_so_basic_pipeline"
        deployment.add_extra(ORCHESTRATOR_DOCKER_IMAGE_KEY, repo_digest)

    def _get_timestamp(self) -> str:
        """Returns the current timestamp."""
        return datetime.now().strftime("%Y-%m-%d-%H-%M-%S")

    def prepare_or_run_pipeline(
        self, deployment: "PipelineDeployment", stack: "Stack"
    ) -> Any:
        """Prepares or runs a pipeline on Sagemaker.

        Args:
            deployment: The deployment to prepare or run.
            stack: The stack to run on.

        Returns:
            The result of the pipeline run.
        """
        session = sagemaker.Session(default_bucket=self.config.bucket)
        image_name = deployment.pipeline.extra[ORCHESTRATOR_DOCKER_IMAGE_KEY]
        sagemaker_steps = []
        for step_name, step in deployment.steps.items():
            command = StepEntrypointConfiguration.get_entrypoint_command()
            arguments = StepEntrypointConfiguration.get_entrypoint_arguments(
                step_name=step_name
            )
            entrypoint = command + arguments

            processor = sagemaker.processing.Processor(
                role=sagemaker.get_execution_role(),
                image_uri=image_name,
                instance_count=1,
                instance_type="ml.t3.medium",
                entrypoint=entrypoint,
                sagemaker_session=session,
                base_job_name=deployment.run_name,
                env={
                    ENV_ZENML_SAGEMAKER_RUN_ID: str(deployment.pipeline_id)
                    + self._get_timestamp()
                },
            )

            sagemaker_step = ProcessingStep(
                name=step.config.name,
                processor=processor,
                depends_on=step.spec.upstream_steps,
            )
            sagemaker_steps.append(sagemaker_step)

        orchestrator_run_name = get_orchestrator_run_name(
            pipeline_name=deployment.pipeline.name
        ).replace("_", "-")

        # construct the pipeline from the sagemaker_steps
        pipeline = Pipeline(
            name=orchestrator_run_name,
            steps=sagemaker_steps,
            sagemaker_session=session,
        )

        pipeline.create(role_arn=sagemaker.get_execution_role())
        pipeline.start()
