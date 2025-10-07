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
from typing import TYPE_CHECKING, Dict, List, Optional, Type, cast

import modal

from zenml.client import Client
from zenml.config.build_configuration import BuildConfiguration
from zenml.config.resource_settings import ByteUnit
from zenml.integrations.modal.flavors import (
    ModalStepOperatorConfig,
    ModalStepOperatorSettings,
)
from zenml.integrations.modal.utils import (
    build_modal_image,
    get_gpu_values,
    get_modal_stack_validator,
    setup_modal_client,
)
from zenml.logger import get_logger
from zenml.stack import StackValidator
from zenml.step_operators import BaseStepOperator

if TYPE_CHECKING:
    from zenml.config.base_settings import BaseSettings
    from zenml.config.step_run_info import StepRunInfo
    from zenml.models import PipelineSnapshotBase

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
        return get_modal_stack_validator()

    def get_docker_builds(
        self, snapshot: "PipelineSnapshotBase"
    ) -> List["BuildConfiguration"]:
        """Get the Docker build configurations for the Modal step operator.

        Args:
            snapshot: The pipeline snapshot.

        Returns:
            A list of Docker build configurations.
        """
        builds = []
        for step_name, step in snapshot.step_configurations.items():
            if step.config.uses_step_operator(self.name):
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
            RuntimeError: If Modal image construction fails, sandbox creation fails,
                sandbox execution fails, or Modal application initialization fails.
        """
        settings = cast(ModalStepOperatorSettings, self.get_settings(info))
        image_name = info.get_image(key=MODAL_STEP_OPERATOR_DOCKER_IMAGE_KEY)
        zc = Client()
        stack = zc.active_stack

        setup_modal_client(
            token_id=self.config.token_id,
            token_secret=self.config.token_secret,
            workspace=self.config.workspace,
            environment=settings.modal_environment
            or self.config.modal_environment,
        )

        try:
            modal_image = build_modal_image(image_name, stack, environment)
        except Exception as e:
            raise RuntimeError(
                "Failed to construct Modal execution environment from your Docker image. "
                "Action required: verify that Modal can access your container registry (check network connectivity "
                "and registry permissions), and that the Docker image can be pulled and extended with additional dependencies. "
                f"Context: image='{image_name}'."
            ) from e

        resource_settings = info.config.resource_settings

        gpu_values = get_gpu_values(settings, resource_settings)

        memory_int = (
            int(mb)
            if (mb := resource_settings.get_memory(ByteUnit.MB))
            else None
        )

        app = modal.App(
            f"zenml-{info.run_name}-{info.step_run_id}-{info.pipeline_step_name}"
        )

        async def run_sandbox() -> None:
            with modal.enable_output():
                try:
                    async with app.run():
                        try:
                            sb = await modal.Sandbox.create.aio(
                                *entrypoint_command,
                                image=modal_image,
                                gpu=gpu_values,
                                cpu=resource_settings.cpu_count,
                                memory=memory_int,
                                cloud=settings.cloud,
                                region=settings.region,
                                app=app,
                                timeout=settings.timeout,
                            )
                        except Exception as e:
                            raise RuntimeError(
                                "Failed to create a Modal sandbox. "
                                "Action required: verify that the referenced Docker image exists and is accessible, "
                                "the requested resources are available (gpu/region/cloud), and your Modal workspace "
                                "permissions allow sandbox creation. "
                                f"Context: image='{image_name}', gpu='{gpu_values}', region='{settings.region}', cloud='{settings.cloud}'."
                            ) from e

                        try:
                            await sb.wait.aio()
                        except Exception as e:
                            raise RuntimeError(
                                "Modal sandbox execution failed. "
                                "Action required: inspect the step logs in Modal, validate your entrypoint command, "
                                "and confirm that dependencies are available in the image/environment."
                            ) from e
                except Exception as e:
                    raise RuntimeError(
                        "Failed to initialize Modal application context (authentication / workspace / environment). "
                        "Action required: make sure you're authenticated with Modal (run 'modal token new' or set "
                        "MODAL_TOKEN_ID and MODAL_TOKEN_SECRET), and that the configured workspace/environment exist "
                        "and you have access to them."
                    ) from e

        asyncio.run(run_sandbox())
