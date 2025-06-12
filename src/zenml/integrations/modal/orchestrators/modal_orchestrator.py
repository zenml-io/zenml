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
    Union,
    cast,
)
from uuid import uuid4

try:
    import modal
except ImportError:
    modal = None  # type: ignore

from zenml.config import ResourceSettings
from zenml.config.base_settings import BaseSettings
from zenml.config.build_configuration import BuildConfiguration
from zenml.config.constants import RESOURCE_SETTINGS_KEY
from zenml.config.resource_settings import ByteUnit
from zenml.entrypoints.pipeline_entrypoint_configuration import (
    PipelineEntrypointConfiguration,
)
from zenml.entrypoints.step_entrypoint_configuration import (
    StepEntrypointConfiguration,
)
from zenml.enums import StackComponentType
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

ENV_ZENML_MODAL_ORCHESTRATOR_RUN_ID = "ZENML_MODAL_ORCHESTRATOR_RUN_ID"


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
    logger.info(f"Running step '{step_name}' in Modal")
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
    logger.info(
        "Starting entire pipeline using PipelineEntrypointConfiguration",
        extra={
            "deployment_id": deployment_id,
            "orchestrator_run_id": orchestrator_run_id,
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


def get_gpu_values(
    settings: "ModalOrchestratorSettings", resource_settings: ResourceSettings
) -> Optional[str]:
    """Get the GPU values for the Modal orchestrator.

    Args:
        settings: The Modal orchestrator settings.
        resource_settings: The resource settings.

    Returns:
        The GPU string if a count is specified, otherwise the GPU type.
    """
    if not settings.gpu:
        return None
    # Prefer resource_settings gpu_count, fallback to 1
    gpu_count = resource_settings.gpu_count or 1
    return f"{settings.gpu}:{gpu_count}" if gpu_count > 1 else settings.gpu


def get_resource_values(
    resource_settings: ResourceSettings,
) -> Tuple[Optional[int], Optional[int]]:
    """Get CPU and memory values from resource settings.

    Args:
        resource_settings: The resource settings.

    Returns:
        Tuple of (cpu_count, memory_mb).
    """
    # Get CPU count
    cpu_count: Optional[int] = None
    if resource_settings.cpu_count is not None:
        cpu_count = int(resource_settings.cpu_count)

    # Convert memory to MB if needed
    memory_mb: Optional[int] = None
    if resource_settings.memory:
        memory_value = resource_settings.get_memory(ByteUnit.MB)
        if memory_value is not None:
            memory_mb = int(memory_value)

    return cpu_count, memory_mb


def get_or_deploy_persistent_modal_app(
    pipeline_name: str,
    zenml_image: Any,
    gpu_values: Optional[str],
    cpu_count: Optional[int],
    memory_mb: Optional[int],
    cloud: Optional[str],
    region: Optional[str],
    timeout: int,
    min_containers: Optional[int],
    max_containers: Optional[int],
    environment_name: Optional[str] = None,
    execution_mode: str = "single_function",
) -> Any:
    """Get or deploy a persistent Modal app with warm containers.

    This function deploys a Modal app that stays alive with warm containers
    for maximum speed between pipeline runs.

    Args:
        pipeline_name: Name of the pipeline.
        zenml_image: Pre-built ZenML Docker image for Modal.
        gpu_values: GPU configuration string.
        cpu_count: Number of CPU cores.
        memory_mb: Memory allocation in MB.
        cloud: Cloud provider to use.
        region: Region to deploy in.
        timeout: Maximum execution timeout.
        min_containers: Minimum containers to keep warm.
        max_containers: Maximum containers to scale to.
        environment_name: Modal environment name.
        execution_mode: Execution mode for the function.

    Returns:
        The Modal function ready for execution.

    Raises:
        Exception: If deployment fails.
    """
    # Use pipeline name + execution mode + 2-hour window for app reuse
    # This ensures apps get redeployed every 2 hours to refresh tokens
    mode_suffix = execution_mode.replace("_", "-")

    # Create a 2-hour timestamp window (rounds down to nearest 2-hour boundary)
    current_time = int(time.time())
    two_hour_window = current_time // (2 * 3600)  # 2 hours = 7200 seconds

    app_name = f"zenml-{pipeline_name.replace('_', '-')}-{mode_suffix}-{two_hour_window}"

    logger.info(f"Getting/deploying persistent Modal app: {app_name}")

    # Create the app
    app = modal.App(app_name)

    # Ensure we have minimum containers for fast startup
    effective_min_containers = min_containers or 1
    effective_max_containers = max_containers or 10

    # Create the execution function based on execution mode
    if execution_mode == "per_step":
        logger.debug("Creating per-step mode for granular execution")
        execution_func: Any = run_step_in_modal
        function_name = "run_step_in_modal"
    else:
        logger.debug("Creating pipeline mode for maximum speed")
        execution_func = run_entire_pipeline
        function_name = "run_entire_pipeline"

    execute_step_func = app.function(
        image=zenml_image,
        gpu=gpu_values,
        cpu=cpu_count,
        memory=memory_mb,
        cloud=cloud,
        region=region,
        timeout=timeout,
        min_containers=effective_min_containers,  # Keep containers warm for speed
        max_containers=effective_max_containers,  # Allow scaling
    )(execution_func)

    # Try to lookup existing app in current 2-hour window, deploy if not found
    try:
        logger.debug(
            f"Checking for Modal app in current 2-hour window: {app_name}"
        )

        try:
            modal.App.lookup(
                app_name, environment_name=environment_name or "main"
            )
            logger.info(
                f"Found existing app '{app_name}' with fresh tokens - reusing warm containers"
            )

            # Try to get the function directly
            try:
                existing_function = modal.Function.from_name(
                    app_name,
                    function_name,
                    environment_name=environment_name or "main",
                )
                logger.debug(
                    "Successfully retrieved function from existing app"
                )
                return existing_function
            except Exception as func_error:
                logger.warning(
                    f"Function lookup failed: {func_error}, redeploying"
                )
                # Fall through to deployment

        except Exception:
            # App not found or other lookup error - deploy fresh app
            logger.debug(
                "No app found for current 2-hour window, deploying fresh app"
            )

        # Deploy the app
        app.deploy(name=app_name, environment_name=environment_name or "main")
        logger.info(
            f"App '{app_name}' deployed with {effective_min_containers} warm containers"
        )
        logger.info(
            f"View real-time logs at: https://modal.com/apps/{app_name}"
        )

    except Exception as e:
        logger.error(f"Deployment failed: {e}")
        raise

    logger.info(
        f"Modal app configured with min_containers={effective_min_containers}, max_containers={effective_max_containers}"
    )

    return execute_step_func


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
        if self.config.token:
            # Set Modal token from config
            os.environ["MODAL_TOKEN_ID"] = self.config.token.get_secret_value()
            logger.info("Using Modal token from orchestrator config")
        else:
            logger.info("Using default Modal authentication (~/.modal.toml)")

        # Set workspace/environment if provided
        if self.config.workspace:
            os.environ["MODAL_WORKSPACE"] = self.config.workspace
        if self.config.environment:
            os.environ["MODAL_ENVIRONMENT"] = self.config.environment

    @property
    def validator(self) -> Optional[StackValidator]:
        """Ensures there is a container registry and artifact store in the stack.

        Returns:
            A `StackValidator` instance.
        """

        def _validate_remote_components(stack: "Stack") -> tuple[bool, str]:
            if stack.artifact_store.config.is_local:
                return False, (
                    "The Modal orchestrator runs code remotely and "
                    "needs to write files into the artifact store, but the "
                    f"artifact store `{stack.artifact_store.name}` of the "
                    "active stack is local. Please ensure that your stack "
                    "contains a remote artifact store when using the Modal "
                    "orchestrator."
                )

            container_registry = stack.container_registry
            assert container_registry is not None

            if container_registry.config.is_local:
                return False, (
                    "The Modal orchestrator runs code remotely and "
                    "needs to push/pull Docker images, but the "
                    f"container registry `{container_registry.name}` of the "
                    "active stack is local. Please ensure that your stack "
                    "contains a remote container registry when using the "
                    "Modal orchestrator."
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

        Raises:
            RuntimeError: If no Docker credentials are found.
            ValueError: If no container registry is found.
        """
        # Get the ZenML-built image that contains all pipeline code
        image_name = self.get_image(deployment=deployment)

        if not stack.container_registry:
            raise ValueError(
                "No Container registry found in the stack. "
                "Please add a container registry and ensure "
                "it is correctly configured."
            )

        if docker_creds := stack.container_registry.credentials:
            docker_username, docker_password = docker_creds
        else:
            raise RuntimeError(
                "No Docker credentials found for the container registry."
            )

        # Create Modal secret for registry authentication
        registry_secret = modal.Secret.from_dict(
            {
                "REGISTRY_USERNAME": docker_username,
                "REGISTRY_PASSWORD": docker_password,
            }
        )

        # Build Modal image from the ZenML-built image
        # Use from_registry to pull the ZenML image with authentication
        # and install Modal dependencies
        zenml_image = (
            modal.Image.from_registry(image_name, secret=registry_secret)
            .pip_install("modal")  # Install Modal in the container
            .env(environment)
        )

        return zenml_image

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
                "Modal is not installed. Please install it with: pip install modal"
            )
        if deployment.schedule:
            logger.warning(
                "Modal Orchestrator currently does not support the "
                "use of schedules. The `schedule` will be ignored "
                "and the pipeline will be run immediately."
            )

        # Setup Modal authentication
        self._setup_modal_client()

        # Generate orchestrator run ID
        orchestrator_run_id = str(uuid4())
        environment[ENV_ZENML_MODAL_ORCHESTRATOR_RUN_ID] = orchestrator_run_id

        # Get settings from pipeline configuration (applies to entire pipeline)
        settings = cast(
            "ModalOrchestratorSettings", self.get_settings(deployment)
        )

        # Get resource settings from pipeline configuration

        pipeline_resource_settings: Union[Dict[str, Any], Any] = (
            deployment.pipeline_configuration.settings.get(
                RESOURCE_SETTINGS_KEY, {}
            )
        )
        if pipeline_resource_settings:
            # Convert to dict if it's a BaseSettings instance
            if hasattr(pipeline_resource_settings, "model_dump"):
                pipeline_resource_dict = (
                    pipeline_resource_settings.model_dump()
                )
            else:
                pipeline_resource_dict = pipeline_resource_settings
            resource_settings = ResourceSettings.model_validate(
                pipeline_resource_dict
            )
        else:
            # Fallback to first step's resource settings if no pipeline-level resources
            if deployment.step_configurations:
                first_step = list(deployment.step_configurations.values())[0]
                resource_settings = first_step.config.resource_settings
            else:
                resource_settings = (
                    ResourceSettings()
                )  # Default empty settings

        # Build Modal image
        zenml_image = self._build_modal_image(deployment, stack, environment)

        # Configure resources from resource settings
        gpu_values = get_gpu_values(settings, resource_settings)
        cpu_count, memory_mb = get_resource_values(resource_settings)

        start_time = time.time()

        # Execute steps using Modal's fast container spin-up with persistent app
        logger.info(
            "Starting pipeline execution with persistent Modal functions"
        )

        step_names = list(deployment.step_configurations.keys())
        logger.debug(f"Found {len(step_names)} steps: {step_names}")

        # Get or deploy persistent Modal app with warm containers
        execute_step = get_or_deploy_persistent_modal_app(
            pipeline_name=deployment.pipeline_configuration.name,
            zenml_image=zenml_image,
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
            execution_mode=settings.execution_mode
            or self.config.execution_mode,  # Use execution mode from settings
        )

        logger.info("Executing with deployed Modal app and warm containers")

        # Execute based on execution mode with improved Modal Function API usage
        execution_mode = settings.execution_mode or self.config.execution_mode
        sync_execution = (
            settings.synchronous
            if hasattr(settings, "synchronous")
            else self.config.synchronous
        )

        def execute_modal_function(
            func_args: Tuple[Any, ...], description: str
        ) -> Any:
            """Execute Modal function with proper sync/async control.

            Args:
                func_args: Arguments to pass to the Modal function.
                description: Description of the operation for logging.

            Returns:
                Result of the Modal function execution.
            """
            logger.info(f"Starting {description}")

            if sync_execution:
                logger.debug("Using .remote() for synchronous execution")
                # .remote() waits for completion but doesn't stream logs
                result = execute_step.remote(*func_args)
                logger.info(f"{description} completed successfully")
                return result
            else:
                logger.debug(
                    "Using .spawn() for asynchronous fire-and-forget execution"
                )
                # .spawn() for fire-and-forget (async)
                function_call = execute_step.spawn(*func_args)
                logger.info(
                    f"{description} started asynchronously (not waiting for completion)"
                )
                return function_call

        if execution_mode == "per_step":
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
                    logger.info("Check Modal dashboard for detailed logs")
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
                logger.info("Check Modal dashboard for detailed logs")
                raise

        run_duration = time.time() - start_time

        # Log completion
        logger.info(
            "Pipeline run has finished in `%s`.",
            string_utils.get_human_readable_time(run_duration),
        )
