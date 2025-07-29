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
"""Modal sandbox executor."""

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union, cast
from uuid import UUID

import modal

from zenml.client import Client
from zenml.config.resource_settings import ByteUnit, ResourceSettings
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
    get_modal_app_name,
    get_or_build_modal_image,
)
from zenml.logger import get_logger

if TYPE_CHECKING:
    from zenml.config.step_configurations import Step
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
        shared_image_cache: Optional[Dict[str, modal.Image]] = None,
        shared_app: Optional[modal.App] = None,
    ):
        """Initialize the Modal sandbox executor.

        Args:
            deployment: The pipeline deployment.
            stack: The ZenML stack.
            environment: Environment variables.
            settings: Modal orchestrator settings.
            shared_image_cache: Pre-built images shared across step executions.
            shared_app: Shared Modal app for the entire pipeline execution.
        """
        self.deployment = deployment
        self.stack = stack
        self.environment = environment
        self.settings = settings
        self.client = Client()
        self.shared_image_cache = shared_image_cache or {}

        # Use shared app if provided, otherwise create new one
        if shared_app:
            self.app = shared_app
            self.app_name = shared_app.name
        else:
            # Create Modal app for this pipeline
            self.app_name = get_modal_app_name(settings, deployment)
            self.app = modal.App.lookup(
                self.app_name,
                create_if_missing=True,
                environment_name=settings.modal_environment,
            )

    # ---------------------------------------------------------------------
    # Resource utilities
    # ---------------------------------------------------------------------

    def _get_settings(
        self, step_name: Optional[str] = None
    ) -> ModalOrchestratorSettings:
        """Get settings for a specific step or pipeline.

        Args:
            step_name: Optional step name for which to fetch settings. If not
                given, pipeline-level settings are returned.

        Returns:
            Pipeline or step settings.
        """
        container: Union["PipelineDeploymentResponse", "Step"] = (
            self.deployment.step_configurations[step_name]
            if step_name
            else self.deployment
        )
        return cast(
            ModalOrchestratorSettings,
            self.stack.orchestrator.get_settings(container),
        )

    def _get_resource_settings(
        self, step_name: Optional[str] = None
    ) -> ResourceSettings:
        """Return validated resource settings for either pipeline or step.

        Args:
            step_name: Optional name of the step for which to fetch resource
                settings. If ``None`` (default), pipeline-level settings are
                returned.

        Returns:
            A validated ``ResourceSettings`` object (never ``None``).
        """
        if step_name:
            return self.deployment.step_configurations[
                step_name
            ].config.resource_settings
        else:
            return self.deployment.pipeline_configuration.resource_settings

        # TODO: Maybe use defaults?
        # resource_settings = ResourceSettings(
        #     cpu_count=1,
        #     memory="1024MB",
        #     gpu_count=0,
        # )

    def _create_environment_secret(self) -> Optional[modal.Secret]:
        """Create a Modal secret containing environment variables.

        Returns:
            Modal secret with environment variables, or None if no env vars.
        """
        if not self.environment:
            return None

        return modal.Secret.from_dict(
            cast(Dict[str, Optional[str]], self.environment)
        )

    def _get_resource_config(
        self, step_name: Optional[str] = None
    ) -> tuple[Optional[str], Optional[int], Optional[int]]:
        """Get validated resource configuration for pipeline or step.

        Args:
            step_name: Name of the step (None for pipeline-level).

        Returns:
            Tuple of (gpu_values, cpu_count, memory_mb) with validated values.
        """
        settings = self._get_settings(step_name)
        resource_settings = self._get_resource_settings(step_name)

        cpu_count: Optional[int] = None
        if resource_settings.cpu_count is not None:
            cpu_count = int(resource_settings.cpu_count)

        memory_mb: Optional[int] = None
        if memory_float := resource_settings.get_memory(ByteUnit.MB):
            memory_mb = int(memory_float)

        gpu_value = None
        gpu_type = settings.gpu
        gpu_count = resource_settings.gpu_count

        if not gpu_type and gpu_count is not None:
            gpu_type = "T4"
            logger.debug(
                f"No GPU type specified for {'step ' + step_name if step_name else 'pipeline'}, "
                f"but gpu_count={gpu_count}. Defaulting to {gpu_type}."
            )

        if gpu_count == 0:
            gpu_value = None
        elif gpu_count is None:
            gpu_value = gpu_type
        else:
            gpu_value = f"{gpu_type}:{gpu_count}"

        return gpu_value, cpu_count, memory_mb

    def _prepare_modal_api_params(
        self,
        entrypoint_command: List[str],
        image: Any,
        gpu: Optional[str],
        cpu: Optional[int],
        memory: Optional[int],
        cloud: Optional[str],
        region: Optional[str],
        app: Any,
        timeout: int,
        secrets: List[modal.Secret],
    ) -> Dict[str, Any]:
        """Prepare and validate Modal API parameters.

        This method ensures that all parameters passed to Modal API are valid
        and handles None values appropriately.

        Args:
            entrypoint_command: Command to execute.
            image: Modal image.
            gpu: GPU configuration string.
            cpu: CPU count.
            memory: Memory in MB.
            cloud: Cloud provider.
            region: Cloud region.
            app: Modal app.
            timeout: Timeout in seconds.
            secrets: List of Modal secrets.

        Returns:
            Dictionary of validated parameters for Modal API.

        Raises:
            ValueError: If required parameters are invalid.
        """
        if not entrypoint_command:
            raise ValueError("Entrypoint command cannot be empty")

        if image is None:
            raise ValueError("Modal image is required")

        if timeout <= 0:
            raise ValueError(f"Timeout must be positive, got {timeout}")

        # Build parameters dictionary
        # Note: entrypoint_command will be passed as *args separately
        params = {
            "image": image,
            "app": app,
            "timeout": timeout,
        }

        # Add optional parameters only if they have valid values
        if gpu is not None:
            # Validate GPU format
            if isinstance(gpu, str) and gpu.strip():
                params["gpu"] = gpu
            else:
                logger.warning(f"Invalid GPU value '{gpu}', ignoring")

        if cpu is not None and cpu > 0:
            params["cpu"] = cpu

        if memory is not None and memory > 0:
            params["memory"] = memory

        if cloud is not None and cloud.strip():
            params["cloud"] = cloud

        if region is not None and region.strip():
            params["region"] = region

        if secrets:
            params["secrets"] = secrets

        # Log final parameters for debugging
        param_summary = {
            k: v
            for k, v in params.items()
            if k not in ["image", "app", "secrets"]  # Skip complex objects
        }
        logger.debug(f"Modal sandbox parameters: {param_summary}")

        return params

    async def _execute_sandbox(
        self,
        entrypoint_command: List[str],
        mode: str,
        step_name: Optional[str] = None,
        run_id: Optional[UUID] = None,
        synchronous: bool = True,
    ) -> None:
        """Execute a sandbox with the given command.

        Args:
            entrypoint_command: Command to execute in the sandbox.
            mode: Execution mode for tagging.
            step_name: Name of the step (for step execution).
            run_id: Pipeline run ID for tagging.
            synchronous: Whether to wait for completion.
        """
        # Get resource configuration with validation
        gpu_values, cpu_count, memory_mb = self._get_resource_config(step_name)

        # Get settings (step-specific for steps, pipeline-level for pipeline)
        if step_name:
            step_settings = self._get_settings(step_name)
            cloud = step_settings.cloud
            region = step_settings.region
            timeout = step_settings.timeout
        else:
            cloud = self.settings.cloud
            region = self.settings.region
            timeout = self.settings.timeout

        # Get or build Modal image (with shared cache support)
        zenml_image = self._get_cached_or_build_image(step_name)

        # Create environment secret
        env_secret = self._create_environment_secret()
        secrets = [env_secret] if env_secret else []

        # Generate tags
        tags = generate_sandbox_tags(
            pipeline_name=self.deployment.pipeline_configuration.name,
            deployment_id=str(self.deployment.id),
            execution_mode=mode,
            step_name=step_name,
            run_id=run_id,
        )

        logger.debug(f"Creating sandbox for {mode.lower()} execution")
        logger.debug(f"Sandbox tags: {tags}")

        # Validate and prepare Modal API parameters
        modal_params = self._prepare_modal_api_params(
            entrypoint_command=entrypoint_command,
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

        with modal.enable_output():
            # Create sandbox with validated parameters
            # Pass entrypoint command as positional args and others as kwargs
            sb = await modal.Sandbox.create.aio(
                *entrypoint_command, **modal_params
            )

            # Set tags
            sb.set_tags(tags)

            if synchronous:
                # Stream output for better user experience
                async for line in sb.stdout:
                    print(line, end="")
                await sb.wait.aio()
            else:
                logger.debug("Sandbox started asynchronously")

            # Store the image ID for future caching after sandbox creation
            # The image should be hydrated after being used in sandbox creation
            await self._store_image_id(zenml_image)

    async def _store_image_id(self, modal_image: modal.Image) -> None:
        """Store the image ID for future caching after sandbox creation.

        Args:
            modal_image: The Modal image that was used.
        """
        try:
            modal_image.hydrate()
            if hasattr(modal_image, "object_id") and modal_image.object_id:
                if self.deployment.build is not None:
                    image_name_key = f"zenml_image_{self.deployment.build.id}"

                    # Store the image ID in Modal's persistent storage
                    pipeline_name = self.deployment.pipeline_configuration.name
                    stored_id = modal.Dict.from_name(
                        f"zenml-image-cache-{pipeline_name}",
                        create_if_missing=True,
                    )
                    stored_id[image_name_key] = modal_image.object_id
                    logger.debug(
                        f"Stored Modal image ID for build {self.deployment.build.id}"
                    )
                else:
                    logger.warning(
                        "Deployment build is None, cannot store image ID"
                    )
            else:
                logger.warning("Image not hydrated after sandbox creation")
        except Exception as e:
            logger.warning(f"Failed to store image ID: {e}")

    def _get_cached_or_build_image(
        self, step_name: Optional[str] = None
    ) -> modal.Image:
        """Get cached Modal image or build new one if not in cache.

        This method first checks the shared image cache for an existing image.
        If found, it returns the cached image. Otherwise, it falls back to
        the standard image building process.

        Args:
            step_name: Name of the step (None for pipeline-level).

        Returns:
            The modal image.
        """
        from zenml.integrations.modal.orchestrators.modal_orchestrator import (
            ModalOrchestrator,
        )

        assert self.deployment.build

        image_name = ModalOrchestrator.get_image(
            deployment=self.deployment, step_name=step_name
        )

        if cached_image := self.shared_image_cache.get(image_name):
            return cached_image

        build_item = self.deployment.build._get_item(
            component_key="ORCHESTRATOR", step=step_name
        )

        return get_or_build_modal_image(
            stack=self.stack,
            pipeline_name=self.deployment.pipeline_configuration.name,
            build_item=build_item,
            build_id=self.deployment.build.id,
        )

    def _get_image_cache_key(
        self, image_name: str, step_name: Optional[str] = None
    ) -> str:
        """Generate a cache key for Modal images.

        Args:
            image_name: The base image name.
            step_name: Name of the step (None for pipeline-level).

        Returns:
            Cache key for the image.

        Raises:
            ValueError: If the deployment does not have a build ID which is
                required to scope the cache key.
        """
        # Use build ID and step name to create unique cache key
        # Include a hash of the image name for uniqueness
        if self.deployment.build is None:
            raise ValueError(
                "Deployment build is None, cannot generate cache key"
            )

        build_id = str(self.deployment.build.id)
        image_hash = str(hash(image_name))[-8:]  # Last 8 chars of hash
        if step_name:
            return f"{build_id}_{step_name}_{image_hash}"
        else:
            return f"{build_id}_pipeline_{image_hash}"

    async def execute_pipeline(
        self,
        run_id: Optional[UUID] = None,
        synchronous: bool = True,
    ) -> None:
        """Execute the entire pipeline in a single sandbox.

        Args:
            run_id: The pipeline run ID.
            synchronous: Whether to wait for completion.
        """
        logger.debug("Executing entire pipeline in single sandbox")

        command = (
            ModalOrchestratorEntrypointConfiguration.get_entrypoint_command()
        )
        args = (
            ModalOrchestratorEntrypointConfiguration.get_entrypoint_arguments(
                deployment_id=self.deployment.id,
                run_id=run_id,
            )
        )

        await self._execute_sandbox(
            entrypoint_command=command + args,
            mode="PIPELINE",
            run_id=run_id,
            synchronous=synchronous,
        )

    async def execute_step(self, step_name: str) -> None:
        """Execute a single step in its own sandbox.

        Args:
            step_name: Name of the step to execute.
        """
        logger.debug(f"Executing step '{step_name}' in separate sandbox")

        command = StepEntrypointConfiguration.get_entrypoint_command()
        args = StepEntrypointConfiguration.get_entrypoint_arguments(
            step_name=step_name, deployment_id=self.deployment.id
        )

        await self._execute_sandbox(
            entrypoint_command=command + args,
            mode="PER_STEP",
            step_name=step_name,
            synchronous=True,
        )
