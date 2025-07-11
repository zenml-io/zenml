#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""Modal sandbox executor for ZenML orchestration."""

from typing import TYPE_CHECKING, Any, Dict, List, Optional

import modal

from zenml.client import Client
from zenml.config.constants import RESOURCE_SETTINGS_KEY
from zenml.config.resource_settings import ResourceSettings
from zenml.entrypoints.step_entrypoint_configuration import (
    StepEntrypointConfiguration,
)
from zenml.integrations.modal.flavors.modal_orchestrator_flavor import (
    ModalOrchestratorSettings,
)
from zenml.integrations.modal.orchestrators.modal_orchestrator_entrypoint_configuration import (
    ModalOrchestratorEntrypointConfiguration,
)
from zenml.integrations.modal.utils import (
    generate_sandbox_tags,
    get_gpu_values,
    get_or_build_modal_image,
    get_resource_settings_from_deployment,
    get_resource_values,
)
from zenml.logger import get_logger

if TYPE_CHECKING:
    from zenml.models import PipelineDeploymentResponse
    from zenml.stack import Stack

logger = get_logger(__name__)


class ModalSandboxExecutor:
    """Handles execution of ZenML pipelines and steps in Modal sandboxes."""

    def __init__(
        self,
        deployment: "PipelineDeploymentResponse",
        stack: "Stack",
        environment: Dict[str, str],
        settings: ModalOrchestratorSettings,
    ):
        """Initialize the Modal sandbox executor.

        Args:
            deployment: The pipeline deployment.
            stack: The ZenML stack.
            environment: Environment variables.
            settings: Modal orchestrator settings.
        """
        self.deployment = deployment
        self.stack = stack
        self.environment = environment
        self.settings = settings
        self.client = Client()

        # Create Modal app for this pipeline
        pipeline_name = deployment.pipeline_configuration.name.replace(
            "_", "-"
        )
        self.app_name = f"zenml-pipeline-{pipeline_name}"
        self.app = modal.App.lookup(
            self.app_name,
            create_if_missing=True,
            environment_name=settings.modal_environment,
        )

    def _build_entrypoint_command(
        self, base_command: List[str], args: List[str]
    ) -> List[str]:
        """Build the complete entrypoint command (without environment variables).

        Environment variables are now passed via secrets parameter to sandbox.

        Args:
            base_command: Base command to execute.
            args: Arguments for the command.

        Returns:
            Complete command without environment variables.
        """
        return base_command + args

    def _get_step_settings(self, step_name: str) -> ModalOrchestratorSettings:
        """Get merged settings for a specific step.

        Args:
            step_name: Name of the step.

        Returns:
            Merged Modal orchestrator settings.
        """
        # Start with pipeline-level settings
        pipeline_settings_dict = self.settings.model_dump()

        # Get step-specific settings
        if step_name in self.deployment.step_configurations:
            step_config = self.deployment.step_configurations[step_name].config
            step_settings = step_config.settings.get("orchestrator.modal")

            if step_settings:
                # Handle both dict and Pydantic model cases
                if hasattr(step_settings, "model_dump"):
                    step_settings_data = step_settings.model_dump()
                else:
                    step_settings_data = step_settings

                step_modal_settings = ModalOrchestratorSettings.model_validate(
                    step_settings_data
                )
                # Merge step settings over pipeline settings
                step_settings_dict = step_modal_settings.model_dump(
                    exclude_unset=True
                )
                for key, value in step_settings_dict.items():
                    if value is not None:
                        pipeline_settings_dict[key] = value

        # Create merged settings from the combined dictionary
        merged_settings = ModalOrchestratorSettings.model_validate(
            pipeline_settings_dict
        )
        return merged_settings

    def _create_environment_secret(self) -> Optional[Any]:
        """Create a Modal secret containing environment variables.

        Returns:
            Modal secret with environment variables, or None if no env vars.
        """
        if not self.environment:
            return None

        # Create secret from environment variables
        # Modal handles efficiency internally
        # Cast to Dict[str, str | None] to match Modal's expected type
        env_dict: Dict[str, Optional[str]] = {
            k: v for k, v in self.environment.items()
        }
        return modal.Secret.from_dict(env_dict)

    def _get_resource_config(
        self, step_name: Optional[str] = None
    ) -> tuple[Optional[str], Optional[int], Optional[int]]:
        """Get resource configuration for pipeline or step.

        Args:
            step_name: Name of the step (None for pipeline-level).

        Returns:
            Tuple of (gpu_values, cpu_count, memory_mb).
        """
        if step_name:
            step_settings = self._get_step_settings(step_name)
            step_config = self.deployment.step_configurations[step_name].config
            resource_settings = step_config.settings.get(RESOURCE_SETTINGS_KEY)
            gpu_values = get_gpu_values(
                step_settings.gpu, resource_settings or ResourceSettings()
            )
        else:
            # Pipeline-level resource settings
            resource_settings = get_resource_settings_from_deployment(
                self.deployment, RESOURCE_SETTINGS_KEY
            )
            gpu_values = get_gpu_values(
                self.settings.gpu, resource_settings or ResourceSettings()
            )

        cpu_count, memory_mb = get_resource_values(
            resource_settings or ResourceSettings()
        )
        return gpu_values, cpu_count, memory_mb

    async def _execute_sandbox(
        self,
        entrypoint_command: List[str],
        execution_mode: str,
        step_name: Optional[str] = None,
        run_id: Optional[str] = None,
        synchronous: bool = True,
    ) -> None:
        """Execute a sandbox with the given command.

        Args:
            entrypoint_command: Command to execute in the sandbox.
            execution_mode: Execution mode for tagging.
            step_name: Name of the step (for step execution).
            run_id: Pipeline run ID for tagging.
            synchronous: Whether to wait for completion.
        """
        # Get resource configuration
        gpu_values, cpu_count, memory_mb = self._get_resource_config(step_name)

        # Get settings (step-specific for steps, pipeline-level for pipeline)
        if step_name:
            step_settings = self._get_step_settings(step_name)
            cloud = step_settings.cloud
            region = step_settings.region
            timeout = step_settings.timeout
        else:
            cloud = self.settings.cloud
            region = self.settings.region
            timeout = self.settings.timeout

        # Get or build Modal image
        image_name = self._get_image_name(step_name)
        zenml_image = get_or_build_modal_image(
            image_name=image_name,
            stack=self.stack,
            pipeline_name=self.deployment.pipeline_configuration.name,
            build_id=str(self.deployment.build.id),
            app=self.app,
        )

        # Create environment secret
        env_secret = self._create_environment_secret()
        secrets = [env_secret] if env_secret else []

        # Generate tags
        tags = generate_sandbox_tags(
            pipeline_name=self.deployment.pipeline_configuration.name,
            deployment_id=str(self.deployment.id),
            execution_mode=execution_mode,
            step_name=step_name,
            run_id=run_id,
        )

        logger.info(f"Creating sandbox for {execution_mode.lower()} execution")
        logger.info(f"Sandbox tags: {tags}")

        with modal.enable_output():
            # Create sandbox with environment variables passed as secrets
            sb = await modal.Sandbox.create.aio(
                *entrypoint_command,
                image=zenml_image,
                gpu=gpu_values,
                cpu=cpu_count,
                memory=memory_mb,
                cloud=cloud,
                region=region,
                app=self.app,
                timeout=timeout,
                secrets=secrets,
            )

            # Set tags
            sb.set_tags(tags)

            if synchronous:
                # Stream output for better user experience
                async for line in sb.stdout:
                    print(line, end="")
                await sb.wait.aio()
            else:
                logger.info("Sandbox started asynchronously")

            # Store the image ID for future caching after sandbox creation
            # The image should be hydrated after being used in sandbox creation
            await self._store_image_id(zenml_image)

    async def _store_image_id(self, zenml_image: Any) -> None:
        """Store the image ID for future caching after sandbox creation.

        Args:
            zenml_image: The Modal image that was used.
        """
        try:
            # After sandbox creation, the image should be hydrated
            zenml_image.hydrate()
            if hasattr(zenml_image, "object_id") and zenml_image.object_id:
                image_name_key = f"zenml_image_{self.deployment.build.id}"

                # Store the image ID in Modal's persistent storage
                pipeline_name = self.deployment.pipeline_configuration.name
                stored_id = modal.Dict.from_name(
                    f"zenml-image-cache-{pipeline_name}",
                    create_if_missing=True,
                )
                stored_id[image_name_key] = zenml_image.object_id
                logger.info(
                    f"Stored Modal image ID for build {self.deployment.build.id}"
                )
            else:
                logger.warning("Image not hydrated after sandbox creation")
        except Exception as e:
            logger.warning(f"Failed to store image ID: {e}")

    def _get_image_name(self, step_name: Optional[str] = None) -> str:
        """Get the image name for the pipeline or step.

        Args:
            step_name: Name of the step (None for pipeline-level).

        Returns:
            Image name to use.
        """
        # Import here to avoid circular imports
        from zenml.integrations.modal.orchestrators.modal_orchestrator import (
            ModalOrchestrator,
        )

        if step_name:
            return ModalOrchestrator.get_image(
                deployment=self.deployment, step_name=step_name
            )
        else:
            return ModalOrchestrator.get_image(deployment=self.deployment)

    async def execute_pipeline(
        self,
        orchestrator_run_id: str,
        run_id: Optional[str] = None,
        synchronous: bool = True,
    ) -> None:
        """Execute the entire pipeline in a single sandbox.

        Args:
            orchestrator_run_id: The orchestrator run ID.
            run_id: The pipeline run ID.
            synchronous: Whether to wait for completion.
        """
        logger.info("Executing entire pipeline in single sandbox")

        # Build entrypoint command
        command = (
            ModalOrchestratorEntrypointConfiguration.get_entrypoint_command()
        )
        args = (
            ModalOrchestratorEntrypointConfiguration.get_entrypoint_arguments(
                deployment_id=self.deployment.id,
                orchestrator_run_id=orchestrator_run_id,
                run_id=run_id or None,
            )
        )
        entrypoint_command = self._build_entrypoint_command(command, args)

        # Execute pipeline sandbox
        await self._execute_sandbox(
            entrypoint_command=entrypoint_command,
            execution_mode="PIPELINE",
            run_id=run_id,
            synchronous=synchronous,
        )

    async def execute_step(self, step_name: str) -> None:
        """Execute a single step in its own sandbox.

        Args:
            step_name: Name of the step to execute.
        """
        logger.info(f"Executing step '{step_name}' in separate sandbox")

        # Build step entrypoint command
        command = StepEntrypointConfiguration.get_entrypoint_command()
        args = StepEntrypointConfiguration.get_entrypoint_arguments(
            step_name=step_name, deployment_id=self.deployment.id
        )
        entrypoint_command = self._build_entrypoint_command(command, args)

        # Execute step sandbox
        await self._execute_sandbox(
            entrypoint_command=entrypoint_command,
            execution_mode="PER_STEP",
            step_name=step_name,
            synchronous=True,  # Steps are always synchronous
        )
