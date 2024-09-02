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
from modal_proto import api_pb2  # type: ignore

from zenml.client import Client
from zenml.config.build_configuration import BuildConfiguration
from zenml.config.resource_settings import ByteUnit, ResourceSettings
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


def get_gpu_values(
    settings: ModalStepOperatorSettings, resource_settings: ResourceSettings
) -> Optional[str]:
    """Get the GPU values for the Modal step operator.

    Args:
        settings: The Modal step operator settings.
        resource_settings: The resource settings.

    Returns:
        The GPU string if a count is specified, otherwise the GPU type.
    """
    if not settings.gpu:
        return None
    gpu_count = resource_settings.gpu_count
    return f"{settings.gpu}:{gpu_count}" if gpu_count else settings.gpu


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
            RuntimeError: If no Docker credentials are found for the container registry.
            ValueError: If no container registry is found in the stack.
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

        my_secret = modal.secret._Secret.from_dict(
            {
                "REGISTRY_USERNAME": docker_username,
                "REGISTRY_PASSWORD": docker_password,
            }
        )

        spec = modal.image.DockerfileSpec(
            commands=[f"FROM {image_name}"], context_files={}
        )

        zenml_image = modal.Image._from_args(
            dockerfile_function=lambda *_, **__: spec,
            force_build=False,
            image_registry_config=modal.image._ImageRegistryConfig(
                api_pb2.REGISTRY_AUTH_TYPE_STATIC_CREDS, my_secret
            ),
        ).env(environment)

        resource_settings = info.config.resource_settings
        gpu_values = get_gpu_values(settings, resource_settings)

        app = modal.App(f"zenml-{info.run_name}-{info.step_run_id}")

        async def run_sandbox() -> asyncio.Future[None]:
            loop = asyncio.get_event_loop()
            future = loop.create_future()
            with modal.enable_output():
                async with app.run():
                    sb = await modal.Sandbox.create.aio(
                        "bash",
                        "-c",
                        " ".join(entrypoint_command),
                        image=zenml_image,
                        gpu=gpu_values,
                        cpu=resource_settings.cpu_count,
                        memory=resource_settings.get_memory(ByteUnit.MB),
                        cloud=settings.cloud,
                        region=settings.region,
                        app=app,
                        timeout=86400, # 24h, the max Modal allows
                    )

                    await sb.wait.aio()  # type: ignore

            future.set_result(None)
            return future

        asyncio.run(run_sandbox())
