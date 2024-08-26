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

import importlib
import os
import subprocess
import tempfile
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple, Type, cast

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
            # ... validation logic ...
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
            raise ValueError(
                "No Docker credentials found for the container registry."
            )

        # get the pydantic version in local environment
        # use it to install the correct version of pydantic in the modal app
        # since it overwrites with 1.x on top of our image
        pydantic_version = importlib.metadata.version("pydantic")
        major, minor, *_ = pydantic_version.split(".")

        # Construct the decorator arguments based on the settings
        decorator_args = []
        if settings.region is not None:
            decorator_args.append(f"region='{settings.region}'")
        if settings.cloud is not None:
            decorator_args.append(f"cloud='{settings.cloud}'")

        # if resource settings are set, add them to the decorator args
        resource_settings = info.config.resource_settings
        if settings.gpu is not None:
            gpu_str = settings.gpu
            if resource_settings.gpu_count is not None:
                gpu_str += f":{resource_settings.gpu_count}"
            decorator_args.append(f"gpu='{gpu_str}'")
        if resource_settings.cpu_count is not None:
            decorator_args.append(f"cpu={resource_settings.cpu_count}")
        if resource_settings.memory is not None:
            decorator_args.append(
                f"memory={resource_settings.get_memory(ByteUnit.MB)}"
            )

        decorator_args_str = ", ".join(decorator_args)

        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".py"
        ) as tmp:
            modal_code = f"""import modal

my_secret = modal.Secret.from_dict({{
    'REGISTRY_USERNAME': '{docker_username}',
    'REGISTRY_PASSWORD': '{docker_password}',
}})

zenml_image = modal.Image.from_registry(tag='{image_name}', secret=my_secret).env({environment}).pip_install("pydantic~={major}.{minor}").run_commands('{" ".join(entrypoint_command)}')

app = modal.App('{info.run_name}')

@app.function(image=zenml_image, {decorator_args_str})
def run_step():
    print("Executing {info.run_name} step...")

if __name__ == "__main__":
    run_step()
"""
            tmp.write(modal_code)
            tmp_filename = tmp.name

        # Run the Modal app using subprocess
        try:
            subprocess.run(
                ["modal", "run", tmp_filename],
                check=True,
                capture_output=True,
                text=True,
            )
            logger.info("Modal app completed successfully.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Modal app exited with code {e.returncode}.")
            logger.error(e.stdout)
            raise
        finally:
            os.remove(tmp_filename)
