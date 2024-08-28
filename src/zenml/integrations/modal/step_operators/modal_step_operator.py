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
"""Modal step operator implementation."""

import asyncio
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple, Type, cast

import modal

from zenml.client import Client
from zenml.config.build_configuration import BuildConfiguration
from zenml.config.resource_settings import ByteUnit
from zenml.enums import StackComponentType
from zenml.integrations.modal.flavors import (
    ModalStepOperatorConfig,
    ModalStepOperatorSettings,
)
from zenml.logger import get_logger
from zenml.stack import Stack, StackValidator
from zenml.step_operators import BaseStepOperator

if TYPE_CHECKING:
    from zenml.config.base_settings import BaseSettings
    from zenml.config.step_run_info import StepRunInfo
    from zenml.models import PipelineDeploymentBase

logger = get_logger(__name__)

MODAL_STEP_OPERATOR_DOCKER_IMAGE_KEY = "modal_step_operator"


class ModalStepOperator(BaseStepOperator):
    """Step operator to run a step on Modal.

    This class defines code that can set up a Modal environment and run
    functions in it.
    """

    @property
    def config(self) -> ModalStepOperatorConfig:
        """Get the Modal step operator configuration.

        Returns:
            The Modal step operator configuration.
        """
        return cast(ModalStepOperatorConfig, self._config)

    @property
    def settings_class(self) -> Optional[Type["BaseSettings"]]:
        """Get the settings class for the Modal step operator.

        Returns:
            The Modal step operator settings class.
        """
        return ModalStepOperatorSettings

    @property
    def validator(self) -> Optional[StackValidator]:
        """Get the stack validator for the Modal step operator.

        Returns:
            The stack validator.
        """

        def _validate_remote_components(stack: "Stack") -> Tuple[bool, str]:
            if stack.artifact_store.config.is_local:
                return False, (
                    "The Modal step operator runs code remotely and "
                    "needs to write files into the artifact store, but the "
                    f"artifact store `{stack.artifact_store.name}` of the "
                    "active stack is local. Please ensure that your stack "
                    "contains a remote artifact store when using the Modal "
                    "step operator."
                )

            container_registry = stack.container_registry
            assert container_registry is not None

            if container_registry.config.is_local:
                return False, (
                    "The Modal step operator runs code remotely and "
                    "needs to push/pull Docker images, but the "
                    f"container registry `{container_registry.name}` of the "
                    "active stack is local. Please ensure that your stack "
                    "contains a remote container registry when using the "
                    "Modal step operator."
                )

            return True, ""

        return StackValidator(
            required_components={
                StackComponentType.CONTAINER_REGISTRY,
                StackComponentType.IMAGE_BUILDER,
            },
            custom_validation_function=_validate_remote_components,
        )

    def get_docker_builds(
        self, deployment: "PipelineDeploymentBase"
    ) -> List["BuildConfiguration"]:
        """Get the Docker build configurations for the Modal step operator.

        Args:
            deployment: The pipeline deployment.

        Returns:
            A list of Docker build configurations.
        """
        builds = []
        for step_name, step in deployment.step_configurations.items():
            if step.config.step_operator == self.name:
                build = BuildConfiguration(
                    key=MODAL_STEP_OPERATOR_DOCKER_IMAGE_KEY,
                    settings=step.config.docker_settings,
                    step_name=step_name,
                )
                builds.append(build)

        return builds

    def launch(
        self,
        info: "StepRunInfo",
        entrypoint_command: List[str],
        environment: Dict[str, str],
    ) -> None:
        """Launch a step run on Modal.

        Args:
            info: The step run information.
            entrypoint_command: The entrypoint command for the step.
            environment: The environment variables for the step.

        Raises:
            subprocess.CalledProcessError: If the modal app exits with a non-zero code.
            ValueError: If no Docker credentials are found for the container registry.
        """
        settings = cast(ModalStepOperatorSettings, self.get_settings(info))
        image_name = info.get_image(key=MODAL_STEP_OPERATOR_DOCKER_IMAGE_KEY)
        zc = Client()
        stack = zc.active_stack

        if not stack.container_registry:
            raise ValueError(
                "No Container registry found in the stack. "
                "Please add a container registry and ensure "
                "it is correctly configured."
            )

        if docker_creds := stack.container_registry.credentials:
            docker_username, docker_password = docker_creds
        else:
            raise RuntimeError(
                "No Docker credentials found for the container registry."
            )

        my_secret = modal.Secret.from_dict(
            {
                "REGISTRY_USERNAME": docker_username,
                "REGISTRY_PASSWORD": docker_password,
            }
        )

        zenml_image = (
            modal.Image.from_registry(tag=image_name, secret=my_secret)
            .env(environment)
            .pip_install("pydantic>=2.7")
            .run_commands(" ".join(entrypoint_command))
        )

        resource_settings = info.config.resource_settings
        gpu_str = settings.gpu
        if resource_settings.gpu_count is not None:
            gpu_str += f":{resource_settings.gpu_count}"

        app = modal.App(f"zenml-{info.run_name}-{info.step_run_id}")

        async def run_sandbox():
            with modal.enable_output():
                async with app.run():
                    modal.Sandbox.create(
                        "bash",
                        "-c",
                        " ".join(entrypoint_command),
                        image=zenml_image,
                        gpu=gpu_str,
                        cpu=resource_settings.cpu_count or None,
                        memory=resource_settings.get_memory(ByteUnit.MB)
                        or None,
                        cloud=settings.cloud or None,
                        region=settings.region or None,
                        app=app,
                    )

        asyncio.run(run_sandbox())
