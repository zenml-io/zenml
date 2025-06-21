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

import os
import sys
import time
import traceback
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    cast,
)
from uuid import uuid4

try:
    import modal
except ImportError:
    modal = None  # type: ignore

from zenml.config.base_settings import BaseSettings
from zenml.config.build_configuration import BuildConfiguration
from zenml.config.constants import RESOURCE_SETTINGS_KEY
from zenml.entrypoints.pipeline_entrypoint_configuration import (
    PipelineEntrypointConfiguration,
)
from zenml.entrypoints.step_entrypoint_configuration import (
    StepEntrypointConfiguration,
)
from zenml.integrations.modal.flavors.modal_orchestrator_flavor import (
    ModalExecutionMode,
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
from zenml.orchestrators import ContainerizedOrchestrator
from zenml.stack import Stack, StackValidator
from zenml.utils import string_utils

if TYPE_CHECKING:
    from zenml.integrations.modal.flavors.modal_orchestrator_flavor import (
        ModalOrchestratorConfig,
        ModalOrchestratorSettings,
    )
    from zenml.models import PipelineDeploymentResponse, PipelineRunResponse
    from zenml.models.v2.core.pipeline_deployment import PipelineDeploymentBase

logger = get_logger(__name__)


def run_step_in_modal(
    step_name: str,
    deployment_id: str,
    orchestrator_run_id: str,
) -> None:
    """Execute a single ZenML step in Modal.

    Args:
        step_name: Name of the step to execute.
        deployment_id: ID of the pipeline deployment.
        orchestrator_run_id: ID of the orchestrator run.

    Raises:
        Exception: If step execution fails.
    """
    # Get pipeline run ID for debugging/logging
    pipeline_run_id = os.environ.get("ZENML_PIPELINE_RUN_ID", "unknown")

    logger.info(
        f"Running step '{step_name}' remotely (pipeline run: {pipeline_run_id})"
    )
    sys.stdout.flush()

    # Set the orchestrator run ID in the Modal environment
    os.environ["ZENML_MODAL_ORCHESTRATOR_RUN_ID"] = orchestrator_run_id

    try:
        logger.info(
            f"Executing step '{step_name}' directly in process for maximum speed"
        )
        sys.stdout.flush()

        # Create the entrypoint arguments
        args = StepEntrypointConfiguration.get_entrypoint_arguments(
            step_name=step_name, deployment_id=deployment_id
        )

        # Create the configuration and run the step
        config = StepEntrypointConfiguration(arguments=args)
        config.run()

        logger.info(f"Step {step_name} completed successfully")
        sys.stdout.flush()

    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"Error executing step {step_name}: {e}")
        logger.debug(f"Full traceback:\n{error_details}")
        sys.stdout.flush()
        raise


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
    # Get pipeline run ID for debugging/logging
    pipeline_run_id = os.environ.get("ZENML_PIPELINE_RUN_ID", "unknown")

    logger.info(
        "Starting entire pipeline using PipelineEntrypointConfiguration",
        extra={
            "deployment_id": deployment_id,
            "orchestrator_run_id": orchestrator_run_id,
            "pipeline_run_id": pipeline_run_id,
        },
    )

    # Set the orchestrator run ID in the Modal environment
    os.environ["ZENML_MODAL_ORCHESTRATOR_RUN_ID"] = orchestrator_run_id

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
            environment=self.config.environment,
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

    def get_docker_builds(
        self, deployment: "PipelineDeploymentBase"
    ) -> List[BuildConfiguration]:
        """Get the Docker build configurations for the Modal orchestrator.

        Args:
            deployment: The pipeline deployment.

        Returns:
            A list of Docker build configurations.
        """
        # Use the standard containerized orchestrator build logic
        # This ensures ZenML builds the image with all pipeline code
        return super().get_docker_builds(deployment)

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
    ) -> Any:
        """Runs the complete pipeline in a single Modal function.

        Args:
            deployment: The pipeline deployment to prepare or run.
            stack: The stack the pipeline will run on.
            environment: Environment variables to set in the orchestration
                environment.
            placeholder_run: An optional placeholder run for the deployment (unused).

        Raises:
            RuntimeError: If Modal is not installed or if a step fails.
            Exception: If pipeline execution fails.
        """
        _ = placeholder_run  # Mark as intentionally unused
        if modal is None:
            raise RuntimeError(
                "Required dependencies not installed. Please install with: pip install modal"
            )
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

        # Include pipeline run ID to prevent conflicts when same container
        # handles multiple pipeline runs rapidly
        pipeline_run_id = placeholder_run.id if placeholder_run else "unknown"

        environment[ENV_ZENML_MODAL_ORCHESTRATOR_RUN_ID] = orchestrator_run_id
        environment["ZENML_PIPELINE_RUN_ID"] = str(pipeline_run_id)

        logger.debug(f"Pipeline run ID: {pipeline_run_id}")
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

        step_names = list(deployment.step_configurations.keys())
        logger.debug(f"Found {len(step_names)} steps: {step_names}")

        # Create the execution function based on execution mode
        execution_mode = settings.execution_mode or self.config.execution_mode
        if execution_mode == ModalExecutionMode.PER_STEP:
            logger.debug("Creating per-step mode for granular execution")
            execution_func: Any = run_step_in_modal
            function_name = "run_step_in_modal"
        else:
            logger.debug("Creating pipeline mode for maximum speed")
            execution_func = run_entire_pipeline
            function_name = "run_entire_pipeline"

        # Get or deploy persistent Modal app with warm containers
        mode_suffix = execution_mode.value.replace("_", "-")
        app_name_base = f"zenml-{deployment.pipeline_configuration.name.replace('_', '-')}-{mode_suffix}"

        execute_step, full_app_name = get_or_deploy_persistent_modal_app(
            app_name_base=app_name_base,
            zenml_image=zenml_image,
            execution_func=execution_func,
            function_name=function_name,
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
            environment_name=settings.environment
            or self.config.environment,  # Use environment from config/settings
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

        if execution_mode == ModalExecutionMode.PER_STEP:
            logger.info("Using per-step mode for granular execution")
            # Execute steps individually
            for step_name in step_names:
                try:
                    execute_modal_function(
                        (step_name, deployment.id, orchestrator_run_id),
                        f"Step '{step_name}' execution",
                    )
                except Exception as e:
                    logger.error(f"Step '{step_name}' failed: {e}")
                    logger.info("Check platform dashboard for detailed logs")
                    raise
        else:
            # Default: execute entire pipeline in one function
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
