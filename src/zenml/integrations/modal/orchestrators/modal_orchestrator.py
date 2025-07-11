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
"""Implementation of a Modal orchestrator."""

import asyncio
import os
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Iterator,
    List,
    Optional,
    Type,
    cast,
)
from uuid import uuid4

import modal

from zenml.config.base_settings import BaseSettings
from zenml.config.constants import RESOURCE_SETTINGS_KEY
from zenml.integrations.modal.flavors.modal_orchestrator_flavor import (
    ModalExecutionMode,
)
from zenml.integrations.modal.orchestrators.modal_orchestrator_entrypoint_configuration import (
    ModalOrchestratorEntrypointConfiguration,
)
from zenml.integrations.modal.utils import (
    ENV_ZENML_MODAL_ORCHESTRATOR_RUN_ID,
    create_modal_stack_validator,
    generate_sandbox_tags,
    get_gpu_values,
    get_or_build_modal_image,
    get_resource_settings_from_deployment,
    get_resource_values,
    setup_modal_client,
)
from zenml.logger import get_logger
from zenml.metadata.metadata_types import MetadataType
from zenml.orchestrators import ContainerizedOrchestrator
from zenml.stack import Stack, StackValidator

if TYPE_CHECKING:
    from zenml.integrations.modal.flavors.modal_orchestrator_flavor import (
        ModalOrchestratorConfig,
        ModalOrchestratorSettings,
    )
    from zenml.models import PipelineDeploymentResponse, PipelineRunResponse

logger = get_logger(__name__)


class ModalOrchestrator(ContainerizedOrchestrator):
    """Orchestrator responsible for running entire pipelines on Modal.

    This orchestrator runs complete pipelines using Modal sandboxes
    for maximum flexibility and efficiency with persistent app architecture.
    """

    @property
    def config(self) -> "ModalOrchestratorConfig":
        """Returns the Modal orchestrator config.

        Returns:
            The Modal orchestrator config.
        """
        return cast("ModalOrchestratorConfig", self._config)

    @property
    def settings_class(self) -> Optional[Type["BaseSettings"]]:
        """Settings class for the Modal orchestrator.

        Returns:
            The settings class.
        """
        from zenml.integrations.modal.flavors.modal_orchestrator_flavor import (
            ModalOrchestratorSettings,
        )

        return ModalOrchestratorSettings

    def _setup_modal_client(self) -> None:
        """Setup Modal client with authentication."""
        setup_modal_client(
            token_id=self.config.token_id,
            token_secret=self.config.token_secret,
            workspace=self.config.workspace,
            environment=self.config.modal_environment,
        )

    @property
    def validator(self) -> Optional[StackValidator]:
        """Ensures there is a container registry and artifact store in the stack.

        Returns:
            A `StackValidator` instance.
        """
        validator: StackValidator = create_modal_stack_validator()
        return validator

    def get_orchestrator_run_id(self) -> str:
        """Returns the active orchestrator run id.

        Raises:
            RuntimeError: If the environment variable specifying the run id
                is not set.

        Returns:
            The orchestrator run id.
        """
        try:
            return os.environ[ENV_ZENML_MODAL_ORCHESTRATOR_RUN_ID]
        except KeyError:
            raise RuntimeError(
                "Unable to read run id from environment variable "
                f"{ENV_ZENML_MODAL_ORCHESTRATOR_RUN_ID}."
            )

    def prepare_or_run_pipeline(
        self,
        deployment: "PipelineDeploymentResponse",
        stack: "Stack",
        environment: Dict[str, str],
        placeholder_run: Optional["PipelineRunResponse"] = None,
    ) -> Optional[Iterator[Dict[str, MetadataType]]]:
        """Runs the complete pipeline in a single Modal function.

        Args:
            deployment: The pipeline deployment to prepare or run.
            stack: The stack the pipeline will run on.
            environment: Environment variables to set in the orchestration
                environment.
            placeholder_run: An optional placeholder run for the deployment (unused).

        Raises:
            Exception: If pipeline execution fails.

        Returns:
            None if the pipeline is executed synchronously, otherwise an iterator of metadata dictionaries.
        """
        if deployment.schedule:
            logger.warning(
                "Serverless Orchestrator currently does not support the "
                "use of schedules. The `schedule` will be ignored "
                "and the pipeline will be run immediately."
            )

        # Setup Modal authentication
        self._setup_modal_client()

        # Generate orchestrator run ID and include pipeline run ID for isolation
        orchestrator_run_id = str(uuid4())

        environment[ENV_ZENML_MODAL_ORCHESTRATOR_RUN_ID] = orchestrator_run_id

        # Pass pipeline run ID for proper isolation (following other orchestrators' pattern)
        if placeholder_run:
            environment["ZENML_PIPELINE_RUN_ID"] = str(placeholder_run.id)
            logger.debug(f"Pipeline run ID: {placeholder_run.id}")

        logger.debug(f"Orchestrator run ID: {orchestrator_run_id}")

        # Get settings from pipeline configuration (applies to entire pipeline)
        settings = cast(
            "ModalOrchestratorSettings", self.get_settings(deployment)
        )

        # Check execution mode
        execution_mode = getattr(
            settings, "execution_mode", ModalExecutionMode.PIPELINE
        )
        logger.info(f"Using execution mode: {execution_mode}")

        # Get resource settings from pipeline configuration
        resource_settings = get_resource_settings_from_deployment(
            deployment, RESOURCE_SETTINGS_KEY
        )

        # Configure resources from resource settings
        gpu_values = get_gpu_values(settings.gpu, resource_settings)
        cpu_count, memory_mb = get_resource_values(resource_settings)

        # Execute pipeline using Modal sandboxes for maximum flexibility
        logger.info("Starting pipeline execution with Modal sandboxes")

        # SANDBOX ARCHITECTURE: Simple persistent app per pipeline
        pipeline_name = deployment.pipeline_configuration.name.replace(
            "_", "-"
        )
        app_name = f"zenml-pipeline-{pipeline_name}"

        # Create Modal app for caching and execution
        app = modal.App.lookup(
            app_name,
            create_if_missing=True,
            environment_name=settings.modal_environment
            or self.config.modal_environment,
        )

        # Get or build Modal image with caching based on deployment ID
        image_name = self.get_image(deployment=deployment)
        zenml_image = get_or_build_modal_image(
            image_name=image_name,
            stack=stack,
            deployment_id=str(deployment.id),
            app=app,
        )

        # Build entrypoint command and args for the orchestrator sandbox
        command = (
            ModalOrchestratorEntrypointConfiguration.get_entrypoint_command()
        )
        args = (
            ModalOrchestratorEntrypointConfiguration.get_entrypoint_arguments(
                deployment_id=deployment.id,
                orchestrator_run_id=orchestrator_run_id,
                run_id=placeholder_run.id if placeholder_run else None,
            )
        )

        # Add environment variables as command prefix
        env_prefix = []
        if environment:
            for key, value in environment.items():
                env_prefix.extend([f"{key}={value}"])

        entrypoint_command = ["env"] + env_prefix + command + args

        # Execute using sandbox
        try:
            asyncio.run(
                self._execute_pipeline_sandbox(
                    app=app,
                    zenml_image=zenml_image,
                    entrypoint_command=entrypoint_command,
                    deployment=deployment,
                    run_id=str(placeholder_run.id)
                    if placeholder_run
                    else None,
                    gpu_values=gpu_values,
                    cpu_count=cpu_count,
                    memory_mb=memory_mb,
                    cloud=settings.cloud or self.config.cloud,
                    region=settings.region or self.config.region,
                    timeout=settings.timeout or self.config.timeout,
                    synchronous=settings.synchronous
                    if hasattr(settings, "synchronous")
                    else self.config.synchronous,
                )
            )
        except Exception as e:
            logger.error(f"Pipeline execution failed: {e}")
            logger.info("Check Modal dashboard for detailed logs")
            raise

        logger.info("Pipeline execution completed successfully")

        return None

    async def _execute_pipeline_sandbox(
        self,
        app: Any,
        zenml_image: Any,
        entrypoint_command: List[str],
        deployment: "PipelineDeploymentResponse",
        run_id: Optional[str] = None,
        gpu_values: Optional[str] = None,
        cpu_count: Optional[int] = None,
        memory_mb: Optional[int] = None,
        cloud: Optional[str] = None,
        region: Optional[str] = None,
        timeout: int = 86400,
        synchronous: bool = True,
    ) -> None:
        """Execute pipeline using Modal sandbox.

        Args:
            app: Modal app instance
            zenml_image: Pre-built ZenML Docker image for Modal
            entrypoint_command: Command to execute in the sandbox
            deployment: Pipeline deployment for tagging
            run_id: Pipeline run ID for tagging
            gpu_values: GPU configuration string
            cpu_count: Number of CPU cores
            memory_mb: Memory allocation in MB
            cloud: Cloud provider to use
            region: Region to deploy in
            timeout: Maximum execution timeout
            synchronous: Whether to wait for completion
        """
        logger.info(f"Using Modal app: {app.name}")

        logger.info("Creating sandbox for pipeline execution")

        # Generate tags for the sandbox
        sandbox_tags = generate_sandbox_tags(
            pipeline_name=deployment.pipeline_configuration.name,
            deployment_id=str(deployment.id),
            execution_mode="PIPELINE",
            run_id=run_id,
        )
        logger.info(f"Sandbox tags: {sandbox_tags}")

        with modal.enable_output():
            # Create sandbox with the entrypoint command
            sb = await modal.Sandbox.create.aio(
                *entrypoint_command,  # Pass as separate arguments to avoid shell quoting issues
                image=zenml_image,
                gpu=gpu_values,
                cpu=cpu_count,
                memory=memory_mb,
                cloud=cloud,
                region=region,
                app=app,
                timeout=timeout,
            )

            # Set tags on the sandbox for organization
            sb.set_tags(sandbox_tags)

            logger.info("Sandbox created, executing pipeline...")

            if synchronous:
                # Stream output while waiting for completion
                logger.info("Streaming pipeline execution logs...")
                async for line in sb.stdout:
                    # Stream logs to stdout with proper formatting
                    print(line, end="")

                # Ensure completion
                await sb.wait.aio()
                logger.info("Pipeline execution completed")
            else:
                logger.info(
                    "Pipeline started asynchronously (not waiting for completion)"
                )
