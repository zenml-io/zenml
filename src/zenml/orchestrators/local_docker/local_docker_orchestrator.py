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
"""Implementation of the ZenML local Docker orchestrator."""

import copy
import os
import sys
import time
from typing import TYPE_CHECKING, Any, Dict, Optional, Type, cast
from uuid import uuid4

from docker.errors import ContainerError

from zenml.config.base_settings import BaseSettings
from zenml.config.global_config import GlobalConfiguration
from zenml.constants import (
    ENV_ZENML_LOCAL_STORES_PATH,
)
from zenml.entrypoints import StepEntrypointConfiguration
from zenml.enums import StackComponentType
from zenml.logger import get_logger
from zenml.orchestrators import (
    BaseOrchestratorConfig,
    BaseOrchestratorFlavor,
    ContainerizedOrchestrator,
)
from zenml.stack import Stack, StackValidator
from zenml.utils import docker_utils, string_utils

if TYPE_CHECKING:
    from zenml.models import PipelineDeploymentResponse, PipelineRunResponse

logger = get_logger(__name__)

ENV_ZENML_DOCKER_ORCHESTRATOR_RUN_ID = "ZENML_DOCKER_ORCHESTRATOR_RUN_ID"


class LocalDockerOrchestrator(ContainerizedOrchestrator):
    """Orchestrator responsible for running pipelines locally using Docker.

    This orchestrator does not allow for concurrent execution of steps and also
    does not support running on a schedule.
    """

    @property
    def settings_class(self) -> Optional[Type["BaseSettings"]]:
        """Settings class for the Local Docker orchestrator.

        Returns:
            The settings class.
        """
        return LocalDockerOrchestratorSettings

    @property
    def validator(self) -> Optional[StackValidator]:
        """Ensures there is an image builder in the stack.

        Returns:
            A `StackValidator` instance.
        """
        return StackValidator(
            required_components={StackComponentType.IMAGE_BUILDER}
        )

    def get_orchestrator_run_id(self) -> str:
        """Returns the active orchestrator run id.

        Raises:
            RuntimeError: If the environment variable specifying the run id
                is not set.

        Returns:
            The orchestrator run id.
        """
        try:
            return os.environ[ENV_ZENML_DOCKER_ORCHESTRATOR_RUN_ID]
        except KeyError:
            raise RuntimeError(
                "Unable to read run id from environment variable "
                f"{ENV_ZENML_DOCKER_ORCHESTRATOR_RUN_ID}."
            )

    def prepare_or_run_pipeline(
        self,
        deployment: "PipelineDeploymentResponse",
        stack: "Stack",
        environment: Dict[str, str],
        placeholder_run: Optional["PipelineRunResponse"] = None,
    ) -> Any:
        """Sequentially runs all pipeline steps in local Docker containers.

        Args:
            deployment: The pipeline deployment to prepare or run.
            stack: The stack the pipeline will run on.
            environment: Environment variables to set in the orchestration
                environment.
            placeholder_run: An optional placeholder run for the deployment.
                This will be deleted in case the pipeline deployment failed.

        Raises:
            RuntimeError: If a step fails.
        """
        if deployment.schedule:
            logger.warning(
                "Local Docker Orchestrator currently does not support the "
                "use of schedules. The `schedule` will be ignored "
                "and the pipeline will be run immediately."
            )

        docker_client = docker_utils._try_get_docker_client_from_env()

        entrypoint = StepEntrypointConfiguration.get_entrypoint_command()

        # Add the local stores path as a volume mount
        stack.check_local_paths()
        local_stores_path = GlobalConfiguration().local_stores_path
        volumes = {
            local_stores_path: {
                "bind": local_stores_path,
                "mode": "rw",
            }
        }
        orchestrator_run_id = str(uuid4())
        environment[ENV_ZENML_DOCKER_ORCHESTRATOR_RUN_ID] = orchestrator_run_id
        environment[ENV_ZENML_LOCAL_STORES_PATH] = local_stores_path
        start_time = time.time()

        # Run each step
        for step_name, step in deployment.step_configurations.items():
            if self.requires_resources_in_orchestration_environment(step):
                logger.warning(
                    "Specifying step resources is not supported for the local "
                    "Docker orchestrator, ignoring resource configuration for "
                    "step %s.",
                    step_name,
                )

            arguments = StepEntrypointConfiguration.get_entrypoint_arguments(
                step_name=step_name, deployment_id=deployment.id
            )

            settings = cast(
                LocalDockerOrchestratorSettings,
                self.get_settings(step),
            )
            image = self.get_image(deployment=deployment, step_name=step_name)

            user = None
            if sys.platform != "win32":
                user = os.getuid()
            logger.info("Running step `%s` in Docker:", step_name)

            run_args = copy.deepcopy(settings.run_args)
            docker_environment = run_args.pop("environment", {})
            docker_environment.update(environment)

            docker_volumes = run_args.pop("volumes", {})
            docker_volumes.update(volumes)

            extra_hosts = run_args.pop("extra_hosts", {})
            extra_hosts["host.docker.internal"] = "host-gateway"

            try:
                logs = docker_client.containers.run(
                    image=image,
                    entrypoint=entrypoint,
                    command=arguments,
                    user=user,
                    volumes=docker_volumes,
                    environment=docker_environment,
                    stream=True,
                    extra_hosts=extra_hosts,
                    **run_args,
                )

                for line in logs:
                    logger.info(line.strip().decode())
            except ContainerError as e:
                error_message = e.stderr.decode()
                raise RuntimeError(error_message)

        run_duration = time.time() - start_time
        logger.info(
            "Pipeline run has finished in `%s`.",
            string_utils.get_human_readable_time(run_duration),
        )


class LocalDockerOrchestratorSettings(BaseSettings):
    """Local Docker orchestrator settings.

    Attributes:
        run_args: Arguments to pass to the `docker run` call. (See
            https://docker-py.readthedocs.io/en/stable/containers.html for a list
            of what can be passed.)
    """

    run_args: Dict[str, Any] = {}


class LocalDockerOrchestratorConfig(
    BaseOrchestratorConfig, LocalDockerOrchestratorSettings
):
    """Local Docker orchestrator config."""

    @property
    def is_local(self) -> bool:
        """Checks if this stack component is running locally.

        Returns:
            True if this config is for a local component, False otherwise.
        """
        return True

    @property
    def is_synchronous(self) -> bool:
        """Whether the orchestrator runs synchronous or not.

        Returns:
            Whether the orchestrator runs synchronous or not.
        """
        return True


class LocalDockerOrchestratorFlavor(BaseOrchestratorFlavor):
    """Flavor for the local Docker orchestrator."""

    @property
    def name(self) -> str:
        """Name of the orchestrator flavor.

        Returns:
            Name of the orchestrator flavor.
        """
        return "local_docker"

    @property
    def docs_url(self) -> Optional[str]:
        """A url to point at docs explaining this flavor.

        Returns:
            A flavor docs url.
        """
        return self.generate_default_docs_url()

    @property
    def sdk_docs_url(self) -> Optional[str]:
        """A url to point at SDK docs explaining this flavor.

        Returns:
            A flavor SDK docs url.
        """
        return self.generate_default_sdk_docs_url()

    @property
    def logo_url(self) -> str:
        """A url to represent the flavor in the dashboard.

        Returns:
            The flavor logo.
        """
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/orchestrator/docker.png"

    @property
    def config_class(self) -> Type[BaseOrchestratorConfig]:
        """Config class for the base orchestrator flavor.

        Returns:
            The config class.
        """
        return LocalDockerOrchestratorConfig

    @property
    def implementation_class(self) -> Type["LocalDockerOrchestrator"]:
        """Implementation class for this flavor.

        Returns:
            Implementation class for this flavor.
        """
        return LocalDockerOrchestrator
