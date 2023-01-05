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
"""Implementation of the AzureML orchestrator."""

import os
import webbrowser
from typing import TYPE_CHECKING, Optional, Type, cast

from azure.ai.ml import MLClient, command, dsl
from azure.ai.ml.entities import Environment
from azure.identity import AzureCliCredential

from zenml.config.base_settings import BaseSettings
from zenml.constants import ORCHESTRATOR_DOCKER_IMAGE_KEY
from zenml.entrypoints import StepEntrypointConfiguration
from zenml.integrations.azure.flavors.azureml_orchestrator_flavor import (
    AzureMLOrchestratorConfig,
    AzureMLOrchestratorSettings,
)
from zenml.logger import get_logger
from zenml.orchestrators.base_orchestrator import BaseOrchestrator
from zenml.orchestrators.utils import get_orchestrator_run_name
from zenml.utils.source_utils import get_source_root_path

if TYPE_CHECKING:
    from zenml.config.pipeline_deployment import PipelineDeployment
    from zenml.stack import Stack


ENV_ZENML_AZUREML_RUN_ID = "ZENML_AZUREML_RUN_ID"
# MAX_POLLING_ATTEMPTS = 100
# POLLING_DELAY = 30

logger = get_logger(__name__)


class AzureMLOrchestrator(BaseOrchestrator):
    """Orchestrator responsible for running pipelines on AzureML."""

    @property
    def config(self) -> AzureMLOrchestratorConfig:
        """Returns the `AzureMLOrchestratorConfig` config.

        Returns:
            The configuration.
        """
        return cast(AzureMLOrchestratorConfig, self._config)

    def get_orchestrator_run_id(self) -> str:
        """Returns the run id of the active orchestrator run.

        Important: This needs to be a unique ID and return the same value for
        all steps of a pipeline run.

        Returns:
            The orchestrator run id.

        Raises:
            RuntimeError: If the run id cannot be read from the environment.
        """
        try:
            return os.environ[ENV_ZENML_AZUREML_RUN_ID]
        except KeyError:
            raise RuntimeError(
                "Unable to read run id from environment variable "
                f"{ENV_ZENML_AZUREML_RUN_ID}."
            )

    def prepare_pipeline_deployment(
        self, deployment: "PipelineDeployment", stack: "Stack"
    ) -> None:
        """Build a Docker image and push it to the container registry.

        Args:
            deployment: The pipeline deployment configuration.
            stack: The stack on which the pipeline will be deployed.
        """
        # docker_image_builder = PipelineDockerImageBuilder()
        # repo_digest = docker_image_builder.build_and_push_docker_image(
        #     deployment=deployment, stack=stack
        # )
        repo_digest = "zenmlazuretest.azurecr.io/zenml@sha256:972ffa104683ace512f76216d234650d9ab02e94c38e33adeedcd11a2e8d64d3"
        deployment.add_extra(ORCHESTRATOR_DOCKER_IMAGE_KEY, repo_digest)

    @property
    def settings_class(self) -> Optional[Type["BaseSettings"]]:
        """Settings class for the AzureML orchestrator.

        Returns:
            The settings class.
        """
        return AzureMLOrchestratorSettings

    def prepare_or_run_pipeline(
        self, deployment: "PipelineDeployment", stack: "Stack"
    ) -> None:
        """Prepares or runs a pipeline on AzureML.

        Args:
            deployment: The deployment to prepare or run.
            stack: The stack to run on.
        """
        if deployment.schedule:
            logger.warning(
                "The AzureML Orchestrator currently does not support the "
                "use of schedules. The `schedule` will be ignored "
                "and the pipeline will be run immediately."
            )

        credential = AzureCliCredential()
        ml_client = MLClient.from_config(credential=credential)
        # get the compute target to use to run our pipeline
        # can be single node or cluster
        cpu_compute_target = "cpu-cluster"
        # cpu_cluster = ml_client.compute.get(cpu_compute_target)

        # get/create the environment that will be used to run each step of the pipeline
        # each step can have its own environment, or they can all use the same one
        # Here you specify your dependencies etc.
        # This can be a Docker image.
        custom_env_name = "zenml-test-env"
        source_directory = get_source_root_path()
        orchestrator_run_name = get_orchestrator_run_name(
            pipeline_name=deployment.pipeline.name
        ).replace("_", "-")

        pipeline_job_env = Environment(
            name=custom_env_name,
            image="zenmlazuretest.azurecr.io/zenml@sha256:972ffa104683ace512f76216d234650d9ab02e94c38e33adeedcd11a2e8d64d3",
        )
        pipeline_job_env = ml_client.environments.create_or_update(
            pipeline_job_env
        )

        steps = []
        for step_name, step in deployment.steps.items():
            container_command = (
                StepEntrypointConfiguration.get_entrypoint_command()
            )
            arguments = StepEntrypointConfiguration.get_entrypoint_arguments(
                step_name=step_name
            )
            entrypoint = container_command + arguments

            job = command(
                environment=pipeline_job_env,
                compute=cpu_compute_target,
                command=" ".join(entrypoint),
                experiment_name=orchestrator_run_name,
                display_name=orchestrator_run_name,
                code=source_directory,
            )
            steps.append(job)

        @dsl.pipeline(
            compute=cpu_compute_target,
        )
        def test_pipeline():
            steps[0]()

        pipeline = test_pipeline()

        pipeline_job = ml_client.jobs.create_or_update(
            pipeline,
            experiment_name="manual_test",
        )
        # open the pipeline in web browser
        webbrowser.open(pipeline_job.studio_url)

        # # mainly for testing purposes, we wait for the pipeline to finish
        # if self.config.synchronous:
        #     logger.info(
        #         "Executing synchronously. Waiting for pipeline to finish..."
        #     )
        #     # TODO: implement a synchronous execution
        #     logger.info("Pipeline completed successfully.")
