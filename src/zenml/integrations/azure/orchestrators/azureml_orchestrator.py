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

import itertools
import os
import webbrowser
from typing import TYPE_CHECKING, Optional, Type, cast

from azure.ai.ml import MLClient, command, dsl
from azure.ai.ml.entities import Environment
from azure.identity import AzureCliCredential
from azureml.core.conda_dependencies import CondaDependencies

import zenml
from zenml.client import Client
from zenml.constants import ENV_ZENML_CONFIG_PATH, ORCHESTRATOR_DOCKER_IMAGE_KEY
from zenml.entrypoints import StepEntrypointConfiguration
from zenml.environment import Environment as ZenMLEnvironment
from zenml.integrations.azure.flavors.azureml_orchestrator_flavor import (
    AzureMLOrchestratorConfig,
    AzureMLOrchestratorSettings,
)
from zenml.logger import get_logger
from zenml.orchestrators.base_orchestrator import BaseOrchestrator
from zenml.orchestrators.utils import get_orchestrator_run_name
from zenml.utils.pipeline_docker_image_builder import (
    DOCKER_IMAGE_ZENML_CONFIG_DIR,
    PipelineDockerImageBuilder,
)
from zenml.utils.source_utils import get_source_root_path

if TYPE_CHECKING:
    from zenml.config import DockerSettings
    from zenml.config.base_settings import BaseSettings
    from zenml.config.pipeline_deployment import PipelineDeployment
    from zenml.stack import Stack


ENV_ZENML_AZUREML_RUN_ID = "ZENML_AZUREML_RUN_ID"
ENV_ACTIVE_DEPLOYMENT = "ZENML_ACTIVE_DEPLOYMENT"

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

    def _prepare_environment(
        self,
        docker_settings: "DockerSettings",
        run_name: str,
        environment_name: Optional[str] = None,
    ) -> Environment:
        """Prepares an AzureML environment.

        Args:
            docker_settings: The docker settings to use.
            run_name: The name of the run.
            environment_name: The name of the environment.

        Returns:
            The prepared environment.
        """
        docker_image_builder = PipelineDockerImageBuilder()
        requirements_files = docker_image_builder._gather_requirements_files(
            docker_settings=docker_settings,
            stack=Client().active_stack,
        )
        requirements = list(
            itertools.chain.from_iterable(
                r[1].split("\n") for r in requirements_files
            )
        )
        requirements.append(f"zenml=={zenml.__version__}")
        logger.info(
            "Using requirements for AzureML step operator environment: %s",
            requirements,
        )
        if environment_name:
            environment = Environment.get(
                workspace=workspace, name=environment_name
            )
            if not environment.python.conda_dependencies:
                environment.python.conda_dependencies = (
                    CondaDependencies.create(
                        python_version=ZenMLEnvironment.python_version()
                    )
                )

            for requirement in requirements:
                environment.python.conda_dependencies.add_pip_package(
                    requirement
                )
        else:
            environment = Environment(name=f"zenml-{run_name}")
            environment.python.conda_dependencies = CondaDependencies.create(
                pip_packages=requirements,
                python_version=ZenMLEnvironment.python_version(),
            )

            if docker_settings.parent_image:
                # replace the default azure base image
                environment.docker.base_image = docker_settings.parent_image

        environment_variables = {
            "ENV_ZENML_PREVENT_PIPELINE_EXECUTION": "True",
        }
        # set credentials to access azure storage
        for key in [
            "AZURE_STORAGE_ACCOUNT_KEY",
            "AZURE_STORAGE_ACCOUNT_NAME",
            "AZURE_STORAGE_CONNECTION_STRING",
            "AZURE_STORAGE_SAS_TOKEN",
        ]:
            value = os.getenv(key)
            if value:
                environment_variables[key] = value

        environment_variables[
            ENV_ZENML_CONFIG_PATH
        ] = f"./{DOCKER_IMAGE_ZENML_CONFIG_DIR}"
        environment_variables.update(docker_settings.environment)

        environment.environment_variables = environment_variables
        return environment

    def prepare_pipeline_deployment(
        self, deployment: "PipelineDeployment", stack: "Stack"
    ) -> None:
        """Build a Docker image and push it to the container registry.

        Args:
            deployment: The pipeline deployment configuration.
            stack: The stack on which the pipeline will be deployed.
        """
        steps_to_run = [
            step
            for step in deployment.steps.values()
            if step.config.step_operator == self.name
        ]
        if not steps_to_run:
            return

        os.environ[ENV_ACTIVE_DEPLOYMENT] = deployment.yaml()

        docker_image_builder = PipelineDockerImageBuilder()
        repo_digest = docker_image_builder.build_and_push_docker_image(
            deployment=deployment, stack=stack
        )
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
        pipeline_job_env
        breakpoint()
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
