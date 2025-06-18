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
from abc import abstractmethod
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple, cast
from uuid import uuid4

import sky
from sky import StatusRefreshMode

from zenml.entrypoints import PipelineEntrypointConfiguration
from zenml.enums import StackComponentType
from zenml.environment import Environment
from zenml.integrations.skypilot.flavors.skypilot_orchestrator_base_vm_config import (
    SkypilotBaseOrchestratorConfig,
    SkypilotBaseOrchestratorSettings,
)
from zenml.integrations.skypilot.orchestrators.skypilot_orchestrator_entrypoint_configuration import (
    SkypilotOrchestratorEntrypointConfiguration,
)
from zenml.integrations.skypilot.utils import (
    create_docker_run_command,
    prepare_docker_setup,
    prepare_launch_kwargs,
    prepare_resources_kwargs,
    prepare_task_kwargs,
    sanitize_cluster_name,
    sky_job_get,
)
from zenml.logger import get_logger
from zenml.orchestrators import (
    ContainerizedOrchestrator,
)
from zenml.orchestrators.utils import get_orchestrator_run_name
from zenml.stack import StackValidator

if TYPE_CHECKING:
    from zenml.models import PipelineDeploymentResponse, PipelineRunResponse
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
    def config(self) -> SkypilotBaseOrchestratorConfig:
        """Returns the `SkypilotBaseOrchestratorConfig` config.

        Returns:
            The configuration.
        """
        return cast(SkypilotBaseOrchestratorConfig, self._config)

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
        placeholder_run: Optional["PipelineRunResponse"] = None,
    ) -> Any:
        """Runs each pipeline step in a separate Skypilot container.

        Args:
            deployment: The pipeline deployment to prepare or run.
            stack: The stack the pipeline will run on.
            environment: Environment variables to set in the orchestration
                environment.
            placeholder_run: An optional placeholder run for the deployment.

        Raises:
            Exception: If the pipeline run fails.
            RuntimeError: If the code is running in a notebook.
        """
        # First check whether the code is running in a notebook.
        if Environment.in_notebook():
            raise RuntimeError(
                "The Skypilot orchestrator cannot run pipelines in a notebook "
                "environment. The reason is that it is non-trivial to create "
                "a Docker image of a notebook. Please consider refactoring "
                "your notebook cells into separate scripts in a Python module "
                "and run the code outside of a notebook when using this "
                "orchestrator."
            )
        if deployment.schedule:
            logger.warning(
                "Skypilot Orchestrator currently does not support the "
                "use of schedules. The `schedule` will be ignored "
                "and the pipeline will be run immediately."
            )

        # Set up some variables for configuration
        orchestrator_run_id = str(uuid4())
        environment[ENV_ZENML_SKYPILOT_ORCHESTRATOR_RUN_ID] = (
            orchestrator_run_id
        )

        settings = cast(
            SkypilotBaseOrchestratorSettings,
            self.get_settings(deployment),
        )

        pipeline_name = deployment.pipeline_configuration.name
        orchestrator_run_name = get_orchestrator_run_name(pipeline_name)

        assert stack.container_registry

        # Get Docker image for the orchestrator pod
        try:
            image = self.get_image(deployment=deployment)
        except KeyError:
            # If no generic pipeline image exists (which means all steps have
            # custom builds) we use a random step image as all of them include
            # dependencies for the active stack
            pipeline_step_name = next(iter(deployment.step_configurations))
            image = self.get_image(
                deployment=deployment, step_name=pipeline_step_name
            )

        different_settings_found = False

        if not self.config.disable_step_based_settings:
            for _, step in deployment.step_configurations.items():
                step_settings = cast(
                    SkypilotBaseOrchestratorSettings,
                    self.get_settings(step),
                )
                if step_settings != settings:
                    different_settings_found = True
                    logger.info(
                        "At least one step has different settings than the "
                        "pipeline. The step with different settings will be "
                        "run in a separate VM.\n"
                        "You can configure the orchestrator to disable this "
                        "behavior by updating the `disable_step_based_settings` "
                        "in your orchestrator configuration "
                        "by running the following command: "
                        "`zenml orchestrator update --disable-step-based-settings=True`"
                    )
                    break

        # Decide which configuration to use based on whether different settings were found
        if (
            not self.config.disable_step_based_settings
            and different_settings_found
        ):
            # Run each step in a separate VM using SkypilotOrchestratorEntrypointConfiguration
            command = SkypilotOrchestratorEntrypointConfiguration.get_entrypoint_command()
            args = SkypilotOrchestratorEntrypointConfiguration.get_entrypoint_arguments(
                run_name=orchestrator_run_name,
                deployment_id=deployment.id,
            )
        else:
            # Run the entire pipeline in one VM using PipelineEntrypointConfiguration
            command = PipelineEntrypointConfiguration.get_entrypoint_command()
            args = PipelineEntrypointConfiguration.get_entrypoint_arguments(
                deployment_id=deployment.id
            )

        entrypoint_str = " ".join(command)
        arguments_str = " ".join(args)

        task_envs = environment.copy()

        # Set up credentials
        self.setup_credentials()

        # Prepare Docker setup
        setup, docker_creds_envs = prepare_docker_setup(
            container_registry_uri=stack.container_registry.config.uri,
            credentials=stack.container_registry.credentials,
            use_sudo=True,  # Base orchestrator uses sudo
        )

        # Update task_envs with Docker credentials
        if docker_creds_envs:
            task_envs.update(docker_creds_envs)

        # Run the entire pipeline

        # Set the service connector AWS profile ENV variable
        self.prepare_environment_variable(set=True)

        try:
            if isinstance(self.cloud, sky.clouds.Kubernetes):
                run_command = f"${{VIRTUAL_ENV:+$VIRTUAL_ENV/bin/}}{entrypoint_str} {arguments_str}"
                setup = None
                down = False
                idle_minutes_to_autostop = None
            else:
                run_command = create_docker_run_command(
                    image=image,
                    entrypoint_str=entrypoint_str,
                    arguments_str=arguments_str,
                    environment=task_envs,
                    docker_run_args=settings.docker_run_args,
                    use_sudo=True,  # Base orchestrator uses sudo
                )
                down = settings.down
                idle_minutes_to_autostop = settings.idle_minutes_to_autostop

            # Create the Task with all parameters and task settings
            task_kwargs = prepare_task_kwargs(
                settings=settings,
                run_command=run_command,
                setup=setup,
                task_envs=task_envs,
                task_name=f"{orchestrator_run_name}",
            )

            task = sky.Task(**task_kwargs)
            logger.debug(f"Running run: {run_command}")

            # Set resources with all parameters and resource settings
            resources_kwargs = prepare_resources_kwargs(
                cloud=self.cloud,
                settings=settings,
                default_instance_type=self.DEFAULT_INSTANCE_TYPE,
                kubernetes_image=image
                if isinstance(self.cloud, sky.clouds.Kubernetes)
                else None,
            )

            task = task.set_resources(sky.Resources(**resources_kwargs))

            launch_new_cluster = True
            if settings.cluster_name:
                status_request_id = sky.status(
                    refresh=StatusRefreshMode.AUTO,
                    cluster_names=[settings.cluster_name],
                )
                cluster_info = sky.stream_and_get(status_request_id)

                if cluster_info:
                    logger.info(
                        f"Found existing cluster {settings.cluster_name}. Reusing..."
                    )
                    launch_new_cluster = False

                else:
                    logger.info(
                        f"Cluster {settings.cluster_name} not found. Launching a new one..."
                    )
                    cluster_name = settings.cluster_name
            else:
                cluster_name = sanitize_cluster_name(
                    f"{orchestrator_run_name}"
                )
                logger.info(
                    f"No cluster name provided. Launching a new cluster with name {cluster_name}..."
                )

            if launch_new_cluster:
                # Prepare launch parameters with additional launch settings
                launch_kwargs = prepare_launch_kwargs(
                    settings=settings,
                    down=down,
                    idle_minutes_to_autostop=idle_minutes_to_autostop,
                )
                logger.info(
                    f"Launching the task on a new cluster: {cluster_name}"
                )
                launch_job_id = sky.launch(
                    task,
                    cluster_name,
                    **launch_kwargs,
                )
                sky_job_get(launch_job_id, settings.stream_logs, cluster_name)

            else:
                # Prepare exec parameters with additional launch settings
                exec_kwargs = {
                    "down": down,
                    "backend": None,
                    **settings.launch_settings,  # Can reuse same settings for exec
                }

                # Remove None values to avoid overriding SkyPilot defaults
                exec_kwargs = {
                    k: v for k, v in exec_kwargs.items() if v is not None
                }

                # Make sure the cluster is up
                start_request_id = sky.start(
                    settings.cluster_name,
                    down=down,
                    idle_minutes_to_autostop=idle_minutes_to_autostop,
                    retry_until_up=settings.retry_until_up,
                )
                sky.stream_and_get(start_request_id)

                logger.info(
                    f"Executing the task on the cluster: {settings.cluster_name}"
                )
                exec_job_id = sky.exec(
                    task,
                    cluster_name=settings.cluster_name,
                    **exec_kwargs,
                )
                assert settings.cluster_name is not None
                sky_job_get(
                    exec_job_id, settings.stream_logs, settings.cluster_name
                )

        except Exception as e:
            logger.error(f"Pipeline run failed: {e}")
            raise

        finally:
            # Unset the service connector AWS profile ENV variable
            self.prepare_environment_variable(set=False)
