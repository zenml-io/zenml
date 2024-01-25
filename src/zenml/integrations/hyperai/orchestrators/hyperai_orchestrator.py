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
import json
import os
import tempfile
import sys
import time
from typing import TYPE_CHECKING, Any, Dict, Optional, Type, Union, cast
from uuid import uuid4
import yaml

from docker.errors import ContainerError
from pydantic import validator

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
from zenml.utils import string_utils

if TYPE_CHECKING:
    from zenml.models import PipelineDeploymentResponse

logger = get_logger(__name__)

ENV_ZENML_DOCKER_ORCHESTRATOR_RUN_ID = "ZENML_DOCKER_ORCHESTRATOR_RUN_ID"


class HyperAIOrchestrator(ContainerizedOrchestrator):
    """Orchestrator responsible for running pipelines on HyperAI instances.
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
    ) -> Any:
        """Sequentially runs all pipeline steps in local Docker containers.

        Args:
            deployment: The pipeline deployment to prepare or run.
            stack: The stack the pipeline will run on.
            environment: Environment variables to set in the orchestration
                environment.

        Raises:
            RuntimeError: If a step fails.
        """
        if deployment.schedule:
            logger.warning(
                "HyperAI orchestrator currently does not support the"
                "use of schedules. The `schedule` will be ignored "
                "and the pipeline will be run immediately."
            )

        # Basic docker-compose definition
        compose_definition = {
            "version": "3",
            "services": {}
        }

        # Add each step as a service to the docker-compose definition
        dependency = None
        for step_name, step in deployment.step_configurations.items():
            image = self.get_image(deployment=deployment, step_name=step_name)
            compose_definition["services"][step_name] = {
                "image": image,
                "container_name": step_name,
                "entrypoint": StepEntrypointConfiguration.get_entrypoint_command(),
                "command": StepEntrypointConfiguration.get_entrypoint_arguments(
                    step_name=step_name, deployment_id=deployment.id
                ),
                "environment": environment,
                "volumes": [
                    f"{GlobalConfiguration().local_stores_path}:{GlobalConfiguration().local_stores_path}"
                ],
            }

            if dependency:
                compose_definition["services"][step_name]["depends_on"] = {
                    dependency: {
                        "condition": "service_completed_successfully"
                    }
                }

        # Can we add multi dependency?

        # Convert into yaml
        compose_definition = yaml.dump(compose_definition)

        # Connect to configured HyperAI instance
        paramiko_client: paramiko.SSHClient
        if connector := self.get_connector():
            paramiko_client = connector.connect()
            if not isinstance(paramiko_client, paramiko.SSHClient):
                raise RuntimeError(
                    f"Expected to receive a `paramiko.SSHClient` object from the "
                    f"linked connector, but got type `{type(boto_session)}`."
                )
        else:
            raise RuntimeError(
                "You must link a HyperAI service connector to the orchestrator."
            )

        # Set up pipeline-runs directory if it doesn't exist
        directory_name = "/home/zenml/pipeline-runs"
        stdin, stdout, stderr = paramiko_client.exec_command(
            f"mkdir -p {directory_name}"
        )

        # Get pipeline run id and create directory for it
        orchestrator_run_id = self.get_orchestrator_run_id()
        directory_name = f"{directory_name}/{orchestrator_run_id}"
        stdin, stdout, stderr = paramiko_client.exec_command(
            f"mkdir -p {directory_name}"
        )
        
        # Create temporary file and write docker-compose file to it
        with tempfile.NamedTemporaryFile(mode="w", delete=True, delete_on_close=False) as f:

            # Write docker-compose file to temporary file
            with f.file as f_:
                f_.write(compose_definition)

            # Scp docker-compose file to HyperAI instance
            scp_client = paramiko_client.open_sftp()
            scp_client.put(
                f.name,
                f"{directory_name}/docker-compose.yaml"
            )
            scp_client.close()


        # Run docker-compose file
        stdin, stdout, stderr = paramiko_client.exec_command(
            f"cd {directory_name} && docker compose up"
        )


class LocalDockerOrchestratorSettings(BaseSettings):
    """Local Docker orchestrator settings.

    Attributes:
        run_args: Arguments to pass to the `docker run` call. (See
            https://docker-py.readthedocs.io/en/stable/containers.html for a list
            of what can be passed.)
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
