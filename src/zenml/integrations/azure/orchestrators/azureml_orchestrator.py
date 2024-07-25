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
"""Implementation of the AzureML Orchestrator."""

import json
import os
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Type, cast

from azure.ai.ml import Input, MLClient, Output
from azure.ai.ml.dsl import pipeline
from azure.ai.ml.entities import (
    CommandComponent,
    Environment,
)
from azure.identity import ClientSecretCredential, DefaultAzureCredential

from zenml.config.base_settings import BaseSettings
from zenml.config.step_configurations import Step
from zenml.enums import StackComponentType
from zenml.integrations.azure.flavors.azureml_orchestrator_flavor import (
    AzureMLOrchestratorConfig,
    AzureMLOrchestratorSettings,
)
from zenml.integrations.azure.orchestrators.azureml_orchestrator_entrypoint_config import (
    AzureMLEntrypointConfiguration,
)
from zenml.logger import get_logger
from zenml.orchestrators import ContainerizedOrchestrator
from zenml.orchestrators.utils import get_orchestrator_run_name
from zenml.stack import StackValidator
from zenml.utils.string_utils import b64_encode

if TYPE_CHECKING:
    from zenml.models import PipelineDeploymentResponse
    from zenml.stack import Stack

logger = get_logger(__name__)

ENV_ZENML_AZUREML_RUN_ID = "AZUREML_ROOT_RUN_ID"


class AzureMLOrchestrator(ContainerizedOrchestrator):
    """Orchestrator responsible for running pipelines on AzureML."""

    @property
    def config(self) -> AzureMLOrchestratorConfig:
        """Returns the `AzureMLOrchestratorConfig` config.

        Returns:
            The configuration.
        """
        return cast(AzureMLOrchestratorConfig, self._config)

    @property
    def settings_class(self) -> Optional[Type["BaseSettings"]]:
        """Settings class for the AzureML orchestrator.

        Returns:
            The settings class.
        """
        return AzureMLOrchestratorSettings

    @property
    def validator(self) -> Optional[StackValidator]:
        """Validates the stack.

        In the remote case, checks that the stack contains a container registry,
        image builder and only remote components.

        Returns:
            A `StackValidator` instance.
        """

        def _validate_remote_components(
            stack: "Stack",
        ) -> Tuple[bool, str]:
            for component in stack.components.values():
                if not component.config.is_local:
                    continue

                return False, (
                    f"The AzureML orchestrator runs pipelines remotely, "
                    f"but the '{component.name}' {component.type.value} is "
                    "a local stack component and will not be available in "
                    "the AzureML step.\nPlease ensure that you always "
                    "use non-local stack components with the AzureML "
                    "orchestrator."
                )

            return True, ""

        return StackValidator(
            required_components={
                StackComponentType.CONTAINER_REGISTRY,
                StackComponentType.IMAGE_BUILDER,
            },
            custom_validation_function=_validate_remote_components,
        )

    def get_orchestrator_run_id(self) -> str:
        """Returns the run id of the active orchestrator run.

        Important: This needs to be a unique ID and return the same value for
        all steps of a pipeline run.

        Returns:
            The orchestrator run id.

        Raises:
            RuntimeError: If the run id cannot be read from the environment.
        """
        try:
            return os.environ[ENV_ZENML_AZUREML_RUN_ID]
        except KeyError:
            raise RuntimeError(
                "Unable to read run id from environment variable "
                f"{ENV_ZENML_AZUREML_RUN_ID}."
            )

    @staticmethod
    def _create_command_component(
        step: Step,
        step_name: str,
        image: str,
        command: List[str],
        arguments: List[str],
    ) -> CommandComponent:
        """Creates a CommandComponent to run on AzureML Pipelines.

        Args:
            step: The step definition in ZenML.
            step_name: The name of the step.
            image: The image to use in the environment
            command: The command to execute the entrypoint with.
            arguments: The arguments to pass into the command.

        Returns:
            the generated AzureML CommandComponent.
        """
        env = Environment(image=image)

        outputs = {}
        if step.config.outputs:
            outputs = {"completed": Output(type="uri_file")}

        inputs = {}
        if step.spec.upstream_steps:
            inputs = {
                f"{upstream_step}": Input(type="uri_file")
                for upstream_step in step.spec.upstream_steps
            }

        return CommandComponent(
            name=step_name,
            display_name=step_name,
            description=f"AzureML CommandComponent for {step_name}.",
            inputs=inputs,
            outputs=outputs,
            environment=env,
            command=" ".join(command + arguments),
        )

    def prepare_or_run_pipeline(
        self,
        deployment: "PipelineDeploymentResponse",
        stack: "Stack",
        environment: Dict[str, str],
    ) -> None:
        """Prepares or runs a pipeline on AzureML.

        Args:
            deployment: The deployment to prepare or run.
            stack: The stack to run on.
            environment: Environment variables to set in the orchestration
                environment.
        """
        # Authentication
        if connector := self.get_connector():
            credentials = connector.connect()
        elif (
            self.config.tenant_id is not None
            and self.config.service_principal_id is not None
            and self.config.service_principal_password is not None
        ):
            credentials = ClientSecretCredential(
                tenant_id=self.config.tenant_id,
                client_id=self.config.service_principal_id,
                client_secret=self.config.service_principal_password,
            )
        else:
            credentials = DefaultAzureCredential()

        # Schedule warning
        if deployment.schedule:
            logger.warning(
                "The AzureML Orchestrator currently does not support the "
                "use of schedules. The `schedule` will be ignored "
                "and the pipeline will be run immediately."
            )

        # Client creation
        ml_client = MLClient(
            credential=credentials,
            subscription_id=self.config.subscription_id,
            resource_group_name=self.config.resource_group,
            workspace_name=self.config.workspace,
        )

        # Run name
        run_name = get_orchestrator_run_name(
            pipeline_name=deployment.pipeline_configuration.name
        )

        # Create components
        components = {}
        for step_name, step in deployment.step_configurations.items():
            # Get the image for each step
            image = self.get_image(deployment=deployment, step_name=step_name)

            # Get the command and arguments
            command = AzureMLEntrypointConfiguration.get_entrypoint_command()
            arguments = (
                AzureMLEntrypointConfiguration.get_entrypoint_arguments(
                    step_name=step_name,
                    deployment_id=deployment.id,
                    environmental_variables=b64_encode(
                        json.dumps(environment)
                    ),
                )
            )

            # Generate an AzureML CommandComponent
            components[step_name] = self._create_command_component(
                step=step,
                step_name=step_name,
                image=image,
                command=command,
                arguments=arguments,
            )

        # Get the pipeline settings
        settings = cast(
            AzureMLOrchestratorSettings, self.get_settings(deployment)
        )

        @pipeline(name=run_name, compute=settings.compute_target)  # type:ignore[call-overload, misc]
        def azureml_pipeline() -> None:
            """Create an AzureML pipeline."""
            # Here we have to track the inputs and outputs so that we can bind
            # the components to each other to execute them in a specific order.
            component_outputs: Dict[str, Any] = {}
            for component_name, component in components.items():
                # Inputs
                component_inputs = {}
                if component.inputs:
                    component_inputs.update(
                        {i: component_outputs[i] for i in component.inputs}
                    )

                # Job
                component_job = component(**component_inputs)

                # Outputs
                if component_job.outputs:
                    component_outputs[component_name] = (
                        component_job.outputs.completed
                    )

        # Create and execute the pipeline job
        pipeline_job = azureml_pipeline()
        ml_client.create_or_update(pipeline_job)
