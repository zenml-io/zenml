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

import json
import os
import sys
import time
from typing import TYPE_CHECKING, Any, Dict, Optional, Type, Union, cast
from uuid import uuid4

from pydantic import validator

from zenml.client import Client
from zenml.config.base_settings import BaseSettings
from zenml.config.global_config import GlobalConfiguration
from zenml.constants import (
    ENV_ZENML_LOCAL_STORES_PATH,
    ORCHESTRATOR_DOCKER_IMAGE_KEY,
)
from zenml.entrypoints import StepEntrypointConfiguration
from zenml.logger import get_logger
from zenml.orchestrators import BaseOrchestrator
from zenml.orchestrators import utils as orchestrator_utils
from zenml.orchestrators.base_orchestrator import (
    BaseOrchestratorConfig,
    BaseOrchestratorFlavor,
)
from zenml.stack import Stack
from zenml.utils import string_utils
from zenml.utils.pipeline_docker_image_builder import PipelineDockerImageBuilder

if TYPE_CHECKING:
    from zenml.config.pipeline_deployment import PipelineDeployment

logger = get_logger(__name__)

ENV_ZENML_DOCKER_ORCHESTRATOR_RUN_ID = "ZENML_DOCKER_ORCHESTRATOR_RUN_ID"


class LocalDockerOrchestrator(BaseOrchestrator):
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

    def prepare_pipeline_deployment(
        self,
        deployment: "PipelineDeployment",
        stack: "Stack",
    ) -> None:
        """Build a Docker image and (maybe) push it to the container registry.

        Args:
            deployment: The pipeline deployment configuration.
            stack: The stack on which the pipeline will be deployed.
        """
        docker_image_builder = PipelineDockerImageBuilder()
        if stack.container_registry:
            repo_digest = docker_image_builder.build_and_push_docker_image(
                deployment=deployment, stack=stack
            )
            deployment.add_extra(ORCHESTRATOR_DOCKER_IMAGE_KEY, repo_digest)
        else:
            # If there is no container registry, we only build the image
            target_image_name = docker_image_builder.get_target_image_name(
                deployment=deployment
            )
            docker_image_builder.build_docker_image(
                target_image_name=target_image_name,
                deployment=deployment,
                stack=stack,
            )
            deployment.add_extra(
                ORCHESTRATOR_DOCKER_IMAGE_KEY, target_image_name
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
        deployment: "PipelineDeployment",
        stack: "Stack",
    ) -> Any:
        """Sequentially runs all pipeline steps in local Docker containers.

        Args:
            deployment: The pipeline deployment to prepare or run.
            stack: The stack the pipeline will run on.
        """
        if deployment.schedule:
            logger.warning(
                "Local Docker Orchestrator currently does not support the"
                "use of schedules. The `schedule` will be ignored "
                "and the pipeline will be run immediately."
            )

        from docker.client import DockerClient

        docker_client = DockerClient.from_env()
        image_name = deployment.pipeline.extra[ORCHESTRATOR_DOCKER_IMAGE_KEY]
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
        environment = {
            ENV_ZENML_DOCKER_ORCHESTRATOR_RUN_ID: orchestrator_run_id,
            ENV_ZENML_LOCAL_STORES_PATH: local_stores_path,
        }
        start_time = time.time()

        # Run each step
        for step_name, step in deployment.steps.items():
            if self.requires_resources_in_orchestration_environment(step):
                logger.warning(
                    "Specifying step resources is not supported for the local "
                    "Docker orchestrator, ignoring resource configuration for "
                    "step %s.",
                    step.config.name,
                )

            arguments = StepEntrypointConfiguration.get_entrypoint_arguments(
                step_name=step_name
            )

            settings = cast(
                LocalDockerOrchestratorSettings,
                self.get_settings(step),
            )

            user = None
            if sys.platform != "win32":
                user = os.getuid()
            logger.info("Running step `%s` in Docker:", step_name)
            logs = docker_client.containers.run(
                image=image_name,
                entrypoint=entrypoint,
                command=arguments,
                user=user,
                volumes=volumes,
                environment=environment,
                stream=True,
                extra_hosts={"host.docker.internal": "host-gateway"},
                **settings.run_args,
            )

            for line in logs:
                logger.info(line.strip().decode())

        run_duration = time.time() - start_time
        run_id = orchestrator_utils.get_run_id_for_orchestrator_run_id(
            orchestrator=self, orchestrator_run_id=orchestrator_run_id
        )
        run_model = Client().zen_store.get_run(run_id)
        logger.info(
            "Pipeline run `%s` has finished in %s.",
            run_model.name,
            string_utils.get_human_readable_time(run_duration),
        )


class LocalDockerOrchestratorSettings(BaseSettings):
    """Local Docker orchestrator settings.

    Attributes:
        run_args: Arguments to pass to the `docker run` call.
    """

    run_args: Dict[str, Any] = {}

    @validator("run_args", pre=True)
    def _convert_json_string(
        cls, value: Union[None, str, Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Converts potential JSON strings passed via the CLI to dictionaries.

        Args:
            value: The value to convert.

        Returns:
            The converted value.

        Raises:
            TypeError: If the value is not a `str`, `Dict` or `None`.
            ValueError: If the value is an invalid json string or a json string
                that does not decode into a dictionary.
        """
        if isinstance(value, str):
            try:
                dict_ = json.loads(value)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid json string '{value}'") from e

            if not isinstance(dict_, Dict):
                raise ValueError(
                    f"Json string '{value}' did not decode into a dictionary."
                )

            return dict_
        elif isinstance(value, Dict) or value is None:
            return value
        else:
            raise TypeError(f"{value} is not a json string or a dictionary.")


class LocalDockerOrchestratorConfig(  # type: ignore[misc] # https://github.com/pydantic/pydantic/issues/4173
    BaseOrchestratorConfig, LocalDockerOrchestratorSettings
):
    """Local Docker orchestrator config."""

    @property
    def is_local(self) -> bool:
        """Checks if this stack component is running locally.

        This designation is used to determine if the stack component can be
        shared with other users or if it is only usable on the local host.

        Returns:
            True if this config is for a local component, False otherwise.
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
