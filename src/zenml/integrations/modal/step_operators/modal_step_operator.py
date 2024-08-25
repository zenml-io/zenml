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

import tempfile
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple, Type, cast

import click
import modal
from modal.cli.run import run

from zenml.client import Client
from zenml.config.build_configuration import BuildConfiguration
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
        """
        settings = cast(ModalStepOperatorSettings, self.get_settings(info))
        image_name = info.get_image(key=MODAL_STEP_OPERATOR_DOCKER_IMAGE_KEY)
        zc = Client()
        stack = zc.active_stack

        if docker_creds := stack.container_registry.credentials:
            docker_username, docker_password = docker_creds

        my_secret = modal.Secret.from_dict(
            {
                "REGISTRY_USERNAME": docker_username,
                "REGISTRY_PASSWORD": docker_password,
            }
        )

        # TODO: replace pydantic superposition with the version from ZenML requirements
        zenml_image = (
            modal.Image.from_registry(
                tag=image_name,
                secret=my_secret,
            )
            .env(environment)
            .pip_install("pydantic~=2.7")
            .run_commands(entrypoint_command)
        )

        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".py"
        ) as tmp:
            modal_code = f"""import modal

my_secret = modal.Secret.from_dict({{
    'REGISTRY_USERNAME': '{docker_username}',
    'REGISTRY_PASSWORD': '{docker_password}',
}})

zenml_image = modal.Image.from_registry(tag='{image_name}', secret=my_secret).env({environment}).pip_install("pydantic~=2.7").run_commands('{" ".join(entrypoint_command)}')

app = modal.App('{info.run_name}')

@app.function(image=zenml_image)
def run_step():
    print("Executing {info.run_name} step...")

if __name__ == "__main__":
    run_step()
"""
            tmp.write(modal_code)
            tmp_filename = tmp.name

        # Create a Click context object
        ctx = click.Context(run)

        # Set the necessary context parameters
        ctx.ensure_object(dict)
        ctx.obj["detach"] = False
        ctx.obj["show_progress"] = True
        ctx.obj["interactive"] = False
        ctx.obj["env"] = None

        run.main(args=[tmp_filename], prog_name="modal run", obj=ctx.obj)
