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
"""Implementation of the ZenML AzureML Step Operator."""

from typing import TYPE_CHECKING, Dict, List, Optional, Tuple, Type, cast

from azure.ai.ml import MLClient, command
from azure.ai.ml.entities import Environment
from azure.core.credentials import TokenCredential
from azure.identity import ClientSecretCredential, DefaultAzureCredential

from zenml.config.build_configuration import BuildConfiguration
from zenml.enums import StackComponentType
from zenml.integrations.azure.azureml_utils import create_or_get_compute
from zenml.integrations.azure.flavors.azureml_step_operator_flavor import (
    AzureMLStepOperatorConfig,
    AzureMLStepOperatorSettings,
)
from zenml.logger import get_logger
from zenml.stack import Stack, StackValidator
from zenml.step_operators import BaseStepOperator

if TYPE_CHECKING:
    from zenml.config.base_settings import BaseSettings
    from zenml.config.step_run_info import StepRunInfo
    from zenml.models import PipelineDeploymentBase

logger = get_logger(__name__)


AZUREML_STEP_OPERATOR_DOCKER_IMAGE_KEY = "azureml_step_operator"


class AzureMLStepOperator(BaseStepOperator):
    """Step operator to run a step on AzureML.

    This class defines code that can set up an AzureML environment and run the
    ZenML entrypoint command in it.
    """

    @property
    def config(self) -> AzureMLStepOperatorConfig:
        """Returns the `AzureMLStepOperatorConfig` config.

        Returns:
            The configuration.
        """
        return cast(AzureMLStepOperatorConfig, self._config)

    @property
    def settings_class(self) -> Optional[Type["BaseSettings"]]:
        """Settings class for the AzureML step operator.

        Returns:
            The settings class.
        """
        return AzureMLStepOperatorSettings

    @property
    def validator(self) -> Optional[StackValidator]:
        """Validates the stack.

        Returns:
            A validator that checks that the stack contains a remote container
            registry and a remote artifact store.
        """

        def _validate_remote_components(
            stack: "Stack",
        ) -> Tuple[bool, str]:
            if stack.artifact_store.config.is_local:
                return False, (
                    "The AzureML step operator runs code remotely and "
                    "needs to write files into the artifact store, but the "
                    f"artifact store `{stack.artifact_store.name}` of the "
                    "active stack is local. Please ensure that your stack "
                    "contains a remote artifact store when using the AzureML "
                    "step operator."
                )

            container_registry = stack.container_registry
            assert container_registry is not None

            if container_registry.config.is_local:
                return False, (
                    "The AzureML step operator runs code remotely and "
                    "needs to push/pull Docker images, but the "
                    f"container registry `{container_registry.name}` of the "
                    "active stack is local. Please ensure that your stack "
                    "contains a remote container registry when using the "
                    "AzureML step operator."
                )

            return True, ""

        return StackValidator(
            required_components={
                StackComponentType.CONTAINER_REGISTRY,
                StackComponentType.IMAGE_BUILDER,
            },
            custom_validation_function=_validate_remote_components,
        )

    def _get_credentials(self) -> TokenCredential:
        """Returns the authentication object for the AzureML environment.

        Returns:
            The authentication object for the AzureML environment.
        """
        # Authentication
        if connector := self.get_connector():
            credentials = connector.connect()
            assert isinstance(credentials, TokenCredential)
            return credentials
        elif (
            self.config.tenant_id
            and self.config.service_principal_id
            and self.config.service_principal_password
        ):
            return ClientSecretCredential(
                tenant_id=self.config.tenant_id,
                client_id=self.config.service_principal_id,
                client_secret=self.config.service_principal_password,
            )
        else:
            return DefaultAzureCredential()

    def get_docker_builds(
        self, deployment: "PipelineDeploymentBase"
    ) -> List["BuildConfiguration"]:
        """Gets the Docker builds required for the component.

        Args:
            deployment: The pipeline deployment for which to get the builds.

        Returns:
            The required Docker builds.
        """
        builds = []
        for step_name, step in deployment.step_configurations.items():
            if step.config.step_operator == self.name:
                build = BuildConfiguration(
                    key=AZUREML_STEP_OPERATOR_DOCKER_IMAGE_KEY,
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
        """Launches a step on AzureML.

        Args:
            info: Information about the step run.
            entrypoint_command: Command that executes the step.
            environment: Environment variables to set in the step operator
                environment.
        """
        settings = cast(AzureMLStepOperatorSettings, self.get_settings(info))
        image_name = info.get_image(key=AZUREML_STEP_OPERATOR_DOCKER_IMAGE_KEY)

        # Client creation
        ml_client = MLClient(
            credential=self._get_credentials(),
            subscription_id=self.config.subscription_id,
            resource_group_name=self.config.resource_group,
            workspace_name=self.config.workspace_name,
        )

        env = Environment(name=f"zenml-{info.run_name}", image=image_name)

        compute_target = create_or_get_compute(
            ml_client, settings, default_compute_name=f"zenml_{self.id}"
        )

        command_job = command(
            name=info.run_name,
            command=" ".join(entrypoint_command),
            environment=env,
            environment_variables=environment,
            compute=compute_target,
            experiment_name=info.pipeline.name,
        )

        job = ml_client.jobs.create_or_update(command_job)

        logger.info(f"AzureML job created with id: {job.id}")
        ml_client.jobs.stream(info.run_name)
