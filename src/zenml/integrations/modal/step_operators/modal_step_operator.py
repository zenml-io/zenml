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
        environment: Optional[Dict[str, str]],
    ) -> None:
        """Launch a step run on Modal.

        Args:
            info: The step run information.
            entrypoint_command: The entrypoint command for the step.
            environment: The environment variables for the step.
        """
        settings = cast(ModalStepOperatorSettings, self.get_settings(info))
        image_name = info.get_image(key=MODAL_STEP_OPERATOR_DOCKER_IMAGE_KEY)
        zc = Client()
        stack = zc.active_stack

        setup_modal_client(
            token_id=self.config.token_id,
            token_secret=self.config.token_secret,
            workspace=self.config.workspace,
            environment=self.config.modal_environment,
        )

        zenml_image = build_modal_image(image_name, stack, environment)

        resource_settings = info.config.resource_settings

        gpu_values = None
        if settings.gpu:
            gpu_count = resource_settings.gpu_count
            if gpu_count == 0:
                gpu_values = None
            elif gpu_count is None:
                gpu_values = settings.gpu
            else:
                gpu_values = f"{settings.gpu}:{gpu_count}"

        app = modal.App(
            f"zenml-{info.run_name}-{info.step_run_id}-{info.pipeline_step_name}"
        )

        async def run_sandbox() -> None:
            with modal.enable_output():
                async with app.run():
                    memory_mb = resource_settings.get_memory(ByteUnit.MB)
                    memory_int = (
                        int(memory_mb) if memory_mb is not None else None
                    )
                    sb = await modal.Sandbox.create.aio(
                        "bash",
                        "-c",
                        " ".join(entrypoint_command),
                        image=zenml_image,
                        gpu=gpu_values,
                        cpu=resource_settings.cpu_count,
                        memory=memory_int,
                        cloud=settings.cloud,
                        region=settings.region,
                        app=app,
                        timeout=settings.timeout,
                    )

                    await sb.wait.aio()

        asyncio.run(run_sandbox())
