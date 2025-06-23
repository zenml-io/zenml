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

import hashlib
import os
import time
import traceback
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Iterator,
    Optional,
    Tuple,
    Type,
    cast,
)
from uuid import uuid4

from zenml.config.base_settings import BaseSettings
from zenml.config.constants import RESOURCE_SETTINGS_KEY
from zenml.entrypoints.pipeline_entrypoint_configuration import (
    PipelineEntrypointConfiguration,
)
from zenml.integrations.modal.utils import (
    ENV_ZENML_MODAL_ORCHESTRATOR_RUN_ID,
    build_modal_image,
    create_modal_stack_validator,
    get_gpu_values,
    get_or_deploy_persistent_modal_app,
    get_resource_settings_from_deployment,
    get_resource_values,
    setup_modal_client,
    stream_modal_logs_and_wait,
)
from zenml.logger import get_logger
from zenml.metadata.metadata_types import MetadataType
from zenml.orchestrators import ContainerizedOrchestrator
from zenml.stack import Stack, StackValidator
from zenml.utils import string_utils

if TYPE_CHECKING:
    from zenml.integrations.modal.flavors.modal_orchestrator_flavor import (
        ModalOrchestratorConfig,
        ModalOrchestratorSettings,
    )
    from zenml.models import PipelineDeploymentResponse, PipelineRunResponse

logger = get_logger(__name__)


def run_entire_pipeline(
    deployment_id: str,
    orchestrator_run_id: str,
) -> None:
    """Execute entire pipeline using PipelineEntrypointConfiguration for maximum efficiency.

    Args:
        deployment_id: ID of the pipeline deployment.
        orchestrator_run_id: ID of the orchestrator run.

    Raises:
        Exception: If pipeline execution fails.
    """
    # Set the orchestrator run ID in the Modal environment
    os.environ[ENV_ZENML_MODAL_ORCHESTRATOR_RUN_ID] = orchestrator_run_id

    try:
        logger.debug("Initializing pipeline entrypoint configuration")

        # Create the entrypoint arguments
        args = PipelineEntrypointConfiguration.get_entrypoint_arguments(
            deployment_id=deployment_id
        )

        logger.debug("Creating pipeline configuration")
        config = PipelineEntrypointConfiguration(arguments=args)

        logger.info("Executing entire pipeline")
        config.run()

        logger.info("Entire pipeline completed successfully")

    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"Error executing pipeline: {e}")
        logger.debug(f"Full traceback:\n{error_details}")
        raise


class ModalOrchestrator(ContainerizedOrchestrator):
    """Orchestrator responsible for running entire pipelines on Modal.

    This orchestrator runs complete pipelines in a single Modal function
    for maximum speed and efficiency, avoiding the overhead of multiple
    step executions.
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

    def _build_modal_image(
        self,
        deployment: "PipelineDeploymentResponse",
        stack: "Stack",
        environment: Dict[str, str],
    ) -> Any:
        """Build the Modal image for pipeline execution.

        Args:
            deployment: The pipeline deployment.
            stack: The stack the pipeline will run on.
            environment: Environment variables to set.

        Returns:
            The configured Modal image.
        """
        # Get the ZenML-built image that contains all pipeline code
        image_name = self.get_image(deployment=deployment)

        return build_modal_image(image_name, stack, environment)

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

        logger.debug(f"Orchestrator run ID: {orchestrator_run_id}")

        # Get settings from pipeline configuration (applies to entire pipeline)
        settings = cast(
            "ModalOrchestratorSettings", self.get_settings(deployment)
        )

        # Get resource settings from pipeline configuration
        resource_settings = get_resource_settings_from_deployment(
            deployment, RESOURCE_SETTINGS_KEY
        )

        # Build Modal image
        zenml_image = self._build_modal_image(deployment, stack, environment)

        # Configure resources from resource settings
        gpu_values = get_gpu_values(settings.gpu, resource_settings)
        cpu_count, memory_mb = get_resource_values(resource_settings)

        start_time = time.time()

        # Execute steps using Modal's fast container spin-up with persistent app
        logger.info(
            "Starting pipeline execution with persistent serverless functions"
        )

        # Use image-based app naming for build-specific persistence
        # This allows multiple pipelines with the same image/build to reuse the same Modal app
        # Different builds get different apps, ensuring proper dependency isolation
        image_name = self.get_image(deployment=deployment)
        # Create a safe app name from the image name (hash if too long)
        safe_image_name = (
            image_name.replace("/", "-").replace(":", "-").replace(".", "-")
        )
        if (
            len(safe_image_name) > 50
        ):  # Modal app names should be reasonable length
            # Use hash to ensure uniqueness while keeping reasonable length
            image_hash = hashlib.md5(image_name.encode()).hexdigest()[:8]
            safe_image_name = f"hashed-{image_hash}"
        app_name_base = f"zenml-{safe_image_name}"

        execute_step, full_app_name = get_or_deploy_persistent_modal_app(
            app_name_base=app_name_base,
            zenml_image=zenml_image,
            execution_func=run_entire_pipeline,
            function_name="run_entire_pipeline",
            deployment=deployment,
            gpu_values=gpu_values,
            cpu_count=cpu_count,  # Use ResourceSettings value or None (Modal default)
            memory_mb=memory_mb,  # Use ResourceSettings value or None (Modal default)
            cloud=settings.cloud or self.config.cloud,
            region=settings.region or self.config.region,
            timeout=settings.timeout or self.config.timeout,
            min_containers=settings.min_containers
            or self.config.min_containers,
            max_containers=settings.max_containers
            or self.config.max_containers,
            environment_name=settings.modal_environment
            or self.config.modal_environment,  # Use modal_environment from config/settings
            app_warming_window_hours=settings.app_warming_window_hours
            or self.config.app_warming_window_hours,
        )

        logger.info(
            "Executing with deployed serverless application and warm containers"
        )

        # Execute based on execution mode with improved Modal Function API usage
        sync_execution = (
            settings.synchronous
            if hasattr(settings, "synchronous")
            else self.config.synchronous
        )

        def execute_modal_function(
            func_args: Tuple[Any, ...], description: str
        ) -> Any:
            """Execute Modal function with proper sync/async control and log streaming.

            Args:
                func_args: Arguments to pass to the Modal function.
                description: Description of the operation for logging.

            Returns:
                Result of the Modal function execution.
            """
            # Always use .spawn() to get a FunctionCall object for log streaming
            function_call = execute_step.spawn(*func_args)

            if sync_execution:
                logger.debug("Using synchronous execution with log streaming")
                # Stream logs while waiting for completion using app name
                return stream_modal_logs_and_wait(
                    function_call, description, full_app_name
                )
            else:
                logger.debug("Using asynchronous fire-and-forget execution")
                logger.info(
                    f"{description} started asynchronously (not waiting for completion)"
                )
                return function_call

        # Execute entire pipeline in one function
        try:
            execute_modal_function(
                (deployment.id, orchestrator_run_id),
                "Pipeline execution",
            )
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            logger.info("Check platform dashboard for detailed logs")
            raise

        run_duration = time.time() - start_time

        # Log completion
        logger.info(
            "Pipeline run has finished in `%s`.",
            string_utils.get_human_readable_time(run_duration),
        )

        return None
