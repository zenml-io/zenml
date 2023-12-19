#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""Implementation of the Skypilot base VM orchestrator."""

import os
import re
from abc import abstractmethod
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, cast
from uuid import uuid4

import sky

from zenml.client import Client
from zenml.entrypoints import StepEntrypointConfiguration
from zenml.enums import StackComponentType
from zenml.integrations.skypilot.flavors.skypilot_orchestrator_base_vm_config import (
    SkypilotBaseOrchestratorSettings,
)
from zenml.logger import get_logger
from zenml.orchestrators import (
    ContainerizedOrchestrator,
)
from zenml.orchestrators import utils as orchestrator_utils
from zenml.stack import StackValidator

if TYPE_CHECKING:
    from zenml.models import PipelineDeploymentResponse
    from zenml.stack import Stack


logger = get_logger(__name__)

ENV_ZENML_SKYPILOT_ORCHESTRATOR_RUN_ID = "ZENML_SKYPILOT_ORCHESTRATOR_RUN_ID"


class SkypilotBaseOrchestrator(ContainerizedOrchestrator):
    """Base class for Orchestrator responsible for running pipelines remotely in a VM.

    This orchestrator does not support running on a schedule.
    """

    # The default instance type to use if none is specified in settings
    DEFAULT_INSTANCE_TYPE: Optional[str] = None

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
                    f"The Skypilot orchestrator runs pipelines remotely, "
                    f"but the '{component.name}' {component.type.value} is "
                    "a local stack component and will not be available in "
                    "the Skypilot step.\nPlease ensure that you always "
                    "use non-local stack components with the Skypilot "
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
        """Returns the active orchestrator run id.

        Raises:
            RuntimeError: If the environment variable specifying the run id
                is not set.

        Returns:
            The orchestrator run id.
        """
        try:
            return os.environ[ENV_ZENML_SKYPILOT_ORCHESTRATOR_RUN_ID]
        except KeyError:
            raise RuntimeError(
                "Unable to read run id from environment variable "
                f"{ENV_ZENML_SKYPILOT_ORCHESTRATOR_RUN_ID}."
            )

    @property
    @abstractmethod
    def cloud(self) -> sky.clouds.Cloud:
        """The type of sky cloud to use.

        Returns:
            A `sky.clouds.Cloud` instance.
        """

    def setup_credentials(self) -> None:
        """Set up credentials for the orchestrator."""
        connector = self.get_connector()
        assert connector is not None
        connector.configure_local_client()

    @abstractmethod
    def prepare_environment_variable(self, set: bool = True) -> None:
        """Set up Environment variables that are required for the orchestrator.

        Args:
            set: Whether to set the environment variables or not.
        """

    def prepare_or_run_pipeline(
        self,
        deployment: "PipelineDeploymentResponse",
        stack: "Stack",
        environment: Dict[str, str],
    ) -> Any:
        """Runs each pipeline step in a separate Skypilot container.

        Args:
            deployment: The pipeline deployment to prepare or run.
            stack: The stack the pipeline will run on.
            environment: Environment variables to set in the orchestration
                environment.

        Raises:
            Exception: If the pipeline run fails.
        """
        if deployment.schedule:
            logger.warning(
                "Skypilot Orchestrator currently does not support the"
                "use of schedules. The `schedule` will be ignored "
                "and the pipeline will be run immediately."
            )

        # Set up some variables for configuration
        orchestrator_run_id = str(uuid4())
        environment[
            ENV_ZENML_SKYPILOT_ORCHESTRATOR_RUN_ID
        ] = orchestrator_run_id
        # Set up some variables for configuration
        orchestrator_run_id = str(uuid4())
        environment[
            ENV_ZENML_SKYPILOT_ORCHESTRATOR_RUN_ID
        ] = orchestrator_run_id

        # Set up credentials
        self.setup_credentials()

        # Set the service connector AWS profile ENV variable
        self.prepare_environment_variable(set=True)

        # Guaranteed by stack validation
        assert stack is not None and stack.container_registry is not None

        docker_creds = stack.container_registry.credentials
        if docker_creds:
            docker_username, docker_password = docker_creds
            setup = (
                f"docker login --username $DOCKER_USERNAME --password "
                f"$DOCKER_PASSWORD {stack.container_registry.config.uri}"
            )
            task_envs = {
                "DOCKER_USERNAME": docker_username,
                "DOCKER_PASSWORD": docker_password,
            }
        else:
            setup = None
            task_envs = None

        unique_resource_configs: Dict[str, List[str]] = {}
        for step_name, step in deployment.step_configurations.items():
            settings = cast(
                SkypilotBaseOrchestratorSettings,
                self.get_settings(step),
            )
            # Handle both str and Dict[str, int] types for accelerators
            if isinstance(settings.accelerators, dict):
                accelerators_hashable = frozenset(
                    settings.accelerators.items()
                )
            elif isinstance(settings.accelerators, str):
                accelerators_hashable = frozenset({(settings.accelerators, 1)})
            else:
                accelerators_hashable = None
            resource_config = (
                settings.instance_type,
                settings.cpus,
                settings.memory,
                settings.disk_size,  # Assuming disk_size is part of the settings
                settings.disk_tier,  # Assuming disk_tier is part of the settings
                settings.use_spot,
                settings.spot_recovery,
                settings.region,
                settings.zone,
                accelerators_hashable,
            )
            cluster_name_parts = [
                self.sanitize_for_cluster_name(part)
                for part in resource_config
                if part is not None
            ]
            cluster_name = "cluster-" + "-".join(cluster_name_parts)
            unique_resource_configs.setdefault(cluster_name, []).append(
                step_name
            )

        # Process each unique resource configuration
        for cluster_name, steps in unique_resource_configs.items():
            # Process each step in the resource configuration
            for step_name in steps:
                step = deployment.step_configurations[step_name]
                settings = cast(
                    SkypilotBaseOrchestratorSettings,
                    self.get_settings(step),
                )
                # Use the step-specific entrypoint configuration
                entrypoint = (
                    StepEntrypointConfiguration.get_entrypoint_command()
                )
                entrypoint_str = " ".join(entrypoint)
                arguments = (
                    StepEntrypointConfiguration.get_entrypoint_arguments(
                        step_name=step_name, deployment_id=deployment.id
                    )
                )
                arguments_str = " ".join(arguments)

                # Set up docker run command
                image = self.get_image(
                    deployment=deployment, step_name=step_name
                )
                docker_environment_str = " ".join(
                    f"-e {k}={v}" for k, v in environment.items()
                )

                # Set up the task
                task = sky.Task(
                    run=f"docker run --rm {docker_environment_str} {image} {entrypoint_str} {arguments_str}",
                    setup=setup,
                    envs=task_envs,
                )
                task = task.set_resources(
                    sky.Resources(
                        cloud=self.cloud,
                        instance_type=settings.instance_type
                        or self.DEFAULT_INSTANCE_TYPE,
                        cpus=settings.cpus,
                        memory=settings.memory,
                        disk_size=settings.disk_size,
                        disk_tier=settings.disk_tier,
                        accelerators=settings.accelerators,
                        accelerator_args=settings.accelerator_args,
                        use_spot=settings.use_spot,
                        spot_recovery=settings.spot_recovery,
                        region=settings.region,
                        zone=settings.zone,
                        image_id=settings.image_id,
                    )
                )

                # Launch the cluster
                try:
                    sky.launch(
                        task,
                        cluster_name,
                        retry_until_up=settings.retry_until_up,
                        idle_minutes_to_autostop=settings.idle_minutes_to_autostop,
                        down=settings.down,
                        stream_logs=settings.stream_logs,
                    )
                except Exception as e:
                    # If there's a resource mismatch, check if this is the last step using this configuration
                    if steps[-1] == step_name:
                        logger.warning(
                            f"Resource mismatch for cluster '{cluster_name}': {e}. "
                            "Attempting to down the existing cluster."
                        )
                        sky.down(cluster_name)
                        # Retry launching the task after bringing down the cluster
                        sky.launch(
                            task,
                            cluster_name,
                            retry_until_up=settings.retry_until_up,
                            idle_minutes_to_autostop=settings.idle_minutes_to_autostop,
                            down=settings.down,
                            stream_logs=settings.stream_logs,
                        )
                    else:
                        logger.warning(
                            f"Resource mismatch for cluster '{cluster_name}', but "
                            "the cluster will be used for subsequent steps. "
                            "Skipping the downing of the cluster: {e}."
                        )

        # Unset the service connector AWS profile ENV variable
        self.prepare_environment_variable(set=False)

        # Log the completion of the pipeline run
        run_id = orchestrator_utils.get_run_id_for_orchestrator_run_id(
            orchestrator=self, orchestrator_run_id=orchestrator_run_id
        )
        run_model = Client().zen_store.get_run(run_id)
        logger.info(
            "Pipeline run `%s` has finished.\n",
            run_model.name,
        )

    def sanitize_for_cluster_name(self, value: Any) -> str:
        """Sanitize the value to be used in a cluster name."""
        # Convert to string, make lowercase, and replace invalid characters with dashes
        return re.sub(r"[^a-z0-9]", "-", str(value).lower())
