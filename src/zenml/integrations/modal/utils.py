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
"""Shared utilities for Modal integration components."""

import os
import subprocess
import threading
import time
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    import modal
except ImportError:
    modal = None  # type: ignore

from zenml.config import ResourceSettings
from zenml.config.resource_settings import ByteUnit
from zenml.enums import StackComponentType
from zenml.logger import get_logger
from zenml.stack import Stack, StackValidator

logger = get_logger(__name__)

# Common environment variable for Modal orchestrator run ID
ENV_ZENML_MODAL_ORCHESTRATOR_RUN_ID = "ZENML_MODAL_ORCHESTRATOR_RUN_ID"


class ModalAuthenticationError(Exception):
    """Exception raised for Modal authentication issues with helpful guidance."""

    def __init__(self, message: str, suggestions: Optional[List[str]] = None):
        """Initialize the authentication error with message and optional suggestions.

        Args:
            message: The error message.
            suggestions: Optional list of suggestions for fixing the issue.
        """
        super().__init__(message)
        self.suggestions = suggestions or []

    def __str__(self) -> str:
        """Return formatted error message with suggestions."""
        base_message = super().__str__()
        if self.suggestions:
            suggestions_text = "\n".join(f"  • {s}" for s in self.suggestions)
            return f"{base_message}\n\nSuggestions:\n{suggestions_text}"
        return base_message


def setup_modal_client(
    token_id: Optional[str] = None,
    token_secret: Optional[str] = None,
    workspace: Optional[str] = None,
    environment: Optional[str] = None,
) -> None:
    """Setup Modal client with authentication.

    Args:
        token_id: Modal API token ID (ak-xxxxx format).
        token_secret: Modal API token secret (as-xxxxx format).
        workspace: Modal workspace name.
        environment: Modal environment name.
    """
    if token_id and token_secret:
        # Validate token format
        if not token_id.startswith("ak-"):
            logger.warning(
                f"Token ID format may be invalid. Expected format: ak-xxxxx, "
                f"got: {token_id[:10]}... (truncated for security)"
            )

        if not token_secret.startswith("as-"):
            logger.warning(
                f"Token secret format may be invalid. Expected format: as-xxxxx, "
                f"got: {token_secret[:10]}... (truncated for security)"
            )

        # Set both token ID and secret
        os.environ["MODAL_TOKEN_ID"] = token_id
        os.environ["MODAL_TOKEN_SECRET"] = token_secret
        logger.info("Using Modal token ID and secret from config")
        logger.debug(f"Token ID starts with: {token_id[:5]}...")
        logger.debug(f"Token secret starts with: {token_secret[:5]}...")

    elif token_id:
        # Validate token format
        if not token_id.startswith("ak-"):
            logger.warning(
                f"Token ID format may be invalid. Expected format: ak-xxxxx, "
                f"got: {token_id[:10]}... (truncated for security)"
            )

        # Only token ID provided
        os.environ["MODAL_TOKEN_ID"] = token_id
        logger.info("Using Modal token ID from config")
        logger.warning(
            "Only token ID provided. Make sure MODAL_TOKEN_SECRET is set "
            "or Modal authentication may fail."
        )
        logger.debug(f"Token ID starts with: {token_id[:5]}...")

    elif token_secret:
        # Validate token format
        if not token_secret.startswith("as-"):
            logger.warning(
                f"Token secret format may be invalid. Expected format: as-xxxxx, "
                f"got: {token_secret[:10]}... (truncated for security)"
            )

        # Only token secret provided (unusual)
        os.environ["MODAL_TOKEN_SECRET"] = token_secret
        logger.warning(
            "Only token secret provided. Make sure MODAL_TOKEN_ID is set "
            "or Modal authentication may fail."
        )
        logger.debug(f"Token secret starts with: {token_secret[:5]}...")

    else:
        logger.info("Using default Modal authentication (~/.modal.toml)")
        # Check if default auth exists
        modal_toml_path = os.path.expanduser("~/.modal.toml")
        if os.path.exists(modal_toml_path):
            logger.debug(f"Found Modal config at {modal_toml_path}")
        else:
            logger.warning(
                f"No Modal config found at {modal_toml_path}. "
                "Run 'modal token new' to set up authentication."
            )

    # Set workspace/environment if provided
    if workspace:
        os.environ["MODAL_WORKSPACE"] = workspace
    if environment:
        os.environ["MODAL_ENVIRONMENT"] = environment


def get_gpu_values(
    gpu_type: Optional[str], resource_settings: ResourceSettings
) -> Optional[str]:
    """Get the GPU values for Modal components.

    Args:
        gpu_type: The GPU type (e.g., "T4", "A100").
        resource_settings: The resource settings.

    Returns:
        The GPU string if a count is specified, otherwise the GPU type.
    """
    if not gpu_type:
        return None
    # Prefer resource_settings gpu_count, fallback to 1
    gpu_count = resource_settings.gpu_count or 1
    return f"{gpu_type}:{gpu_count}" if gpu_count > 1 else gpu_type


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


def build_modal_image(
    image_name: str,
    stack: "Stack",
    environment: Dict[str, str],
) -> Any:
    """Build a Modal image from a ZenML-built Docker image.

    Args:
        image_name: The name of the Docker image to use as base.
        stack: The ZenML stack containing container registry.
        environment: Environment variables to set in the image.

    Returns:
        The configured Modal image.

    Raises:
        RuntimeError: If no Docker credentials are found.
        ValueError: If no container registry is found.
    """
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


def create_modal_stack_validator() -> StackValidator:
    """Create a stack validator for Modal components.

    Returns:
        A StackValidator that ensures remote artifact store and container registry.
    """

    def _validate_remote_components(stack: "Stack") -> Tuple[bool, str]:
        if stack.artifact_store.config.is_local:
            return False, (
                "Modal components run code remotely and "
                "need to write files into the artifact store, but the "
                f"artifact store `{stack.artifact_store.name}` of the "
                "active stack is local. Please ensure that your stack "
                "contains a remote artifact store when using Modal "
                "components."
            )

        container_registry = stack.container_registry
        assert container_registry is not None

        if container_registry.config.is_local:
            return False, (
                "Modal components run code remotely and "
                "need to push/pull Docker images, but the "
                f"container registry `{container_registry.name}` of the "
                "active stack is local. Please ensure that your stack "
                "contains a remote container registry when using Modal "
                "components."
            )

        return True, ""

    return StackValidator(
        required_components={
            StackComponentType.CONTAINER_REGISTRY,
            StackComponentType.IMAGE_BUILDER,
        },
        custom_validation_function=_validate_remote_components,
    )


def get_or_deploy_persistent_modal_app(
    app_name_base: str,
    zenml_image: Any,
    execution_func: Any,
    function_name: str,
    deployment: Any,
    gpu_values: Optional[str] = None,
    cpu_count: Optional[int] = None,
    memory_mb: Optional[int] = None,
    cloud: Optional[str] = None,
    region: Optional[str] = None,
    timeout: int = 86400,
    min_containers: Optional[int] = None,
    max_containers: Optional[int] = None,
    environment_name: Optional[str] = None,
    app_warming_window_hours: float = 2.0,
) -> Tuple[Any, str]:
    """Get or deploy a persistent Modal app with warm containers.

    This function deploys a Modal app that stays alive with warm containers
    for maximum speed between runs. The app name includes both time window
    and build checksum to ensure fresh deployments only when builds actually change.

    Args:
        app_name_base: Base name for the app (will be suffixed with timestamp and build hash).
        zenml_image: Pre-built ZenML Docker image for Modal.
        execution_func: The function to execute in the Modal app.
        function_name: Name of the function in the app.
        deployment: The pipeline deployment containing build information.
        gpu_values: GPU configuration string.
        cpu_count: Number of CPU cores.
        memory_mb: Memory allocation in MB.
        cloud: Cloud provider to use.
        region: Region to deploy in.
        timeout: Maximum execution timeout.
        min_containers: Minimum containers to keep warm.
        max_containers: Maximum containers to scale to.
        environment_name: Modal environment name.
        app_warming_window_hours: Hours for app name window to enable reuse.

    Returns:
        Tuple of (Modal function ready for execution, full app name).

    Raises:
        Exception: If deployment fails.
    """
    # Create timestamp window for app reuse (rounds down to nearest window boundary)
    current_time = int(time.time())
    window_seconds = int(
        app_warming_window_hours * 3600
    )  # Convert hours to seconds
    time_window = current_time // window_seconds

    # Generate build identifier to ensure fresh deployments only when builds actually change
    # Use deployment build checksum which only changes when Docker settings, requirements, etc. change
    build_hash = "no-build"
    if deployment.build and deployment.build.checksum:
        # Use first 8 characters of build checksum for compact identifier
        build_hash = deployment.build.checksum[:8]
        logger.debug(f"Using build checksum: {deployment.build.checksum}")
    else:
        logger.warning(
            "No build checksum available, using fallback identifier"
        )

    # Include both time window and build hash in app name
    app_name = f"{app_name_base}-{time_window}-{build_hash}"

    logger.info(f"Getting/deploying persistent Modal app: {app_name}")
    logger.debug(
        f"App name includes time window: {time_window}, build hash: {build_hash}"
    )

    # Create the app
    app = modal.App(app_name)

    # Ensure we have minimum containers for fast startup
    effective_min_containers = min_containers or 1
    effective_max_containers = max_containers or 10

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

    # Try to lookup existing app with matching time window and image, deploy if not found
    try:
        logger.debug(
            f"Checking for Modal app with time window {time_window} and build hash {build_hash}: {app_name}"
        )

        try:
            modal.App.lookup(
                app_name, environment_name=environment_name or "main"
            )
            logger.info(
                f"Found existing app '{app_name}' with matching build and fresh time window - reusing warm containers"
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
                return existing_function, app_name
            except Exception as func_error:
                logger.warning(
                    f"Function lookup failed: {func_error}, redeploying"
                )
                # Fall through to deployment

        except Exception:
            # App not found or other lookup error - deploy fresh app
            logger.debug(
                "No app found for current time window and build hash, deploying fresh app"
            )

        # Deploy the app with better error handling
        try:
            app.deploy(
                name=app_name, environment_name=environment_name or "main"
            )
            logger.info(
                f"App '{app_name}' deployed with {effective_min_containers} warm containers"
            )
            logger.info(
                f"View real-time logs at: https://modal.com/apps/{app_name}"
            )
        except Exception as deploy_error:
            error_message = str(deploy_error)
            if (
                "Token ID is malformed" in error_message
                or "UNAUTHENTICATED" in error_message
            ):
                raise ModalAuthenticationError(
                    "Modal authentication failed. Token ID or secret is invalid.",
                    suggestions=[
                        "Check that token_id starts with 'ak-' and token_secret starts with 'as-'",
                        "Get new tokens from Modal dashboard: https://modal.com/tokens",
                        "Or run 'modal token new' to set up ~/.modal.toml authentication",
                        "Ensure both token_id AND token_secret are provided in orchestrator config",
                    ],
                ) from deploy_error
            else:
                # Re-raise other deployment errors as-is
                raise

    except Exception as e:
        logger.error(f"Deployment failed: {e}")
        raise

    logger.info(
        f"Modal app configured with min_containers={effective_min_containers}, max_containers={effective_max_containers}"
    )

    return execute_step_func, app_name


def get_resource_settings_from_deployment(
    deployment: Any,
    resource_settings_key: str = "resources",
) -> ResourceSettings:
    """Extract resource settings from pipeline deployment.

    Args:
        deployment: The pipeline deployment.
        resource_settings_key: Key to look for resource settings.

    Returns:
        ResourceSettings object with the configuration.
    """
    pipeline_resource_settings: Union[Dict[str, Any], Any] = (
        deployment.pipeline_configuration.settings.get(
            resource_settings_key, {}
        )
    )
    if pipeline_resource_settings:
        # Convert to dict if it's a BaseSettings instance
        if hasattr(pipeline_resource_settings, "model_dump"):
            pipeline_resource_dict = pipeline_resource_settings.model_dump()
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
            resource_settings = ResourceSettings()  # Default empty settings

    return resource_settings


def stream_modal_logs_and_wait(
    function_call: Any,
    description: str,
    app_name: str,
    check_interval: float = 2.0,
) -> Any:
    """Stream logs from Modal app using CLI and wait for FunctionCall completion.

    Args:
        function_call: The Modal FunctionCall object from .spawn()
        description: Description of the operation for logging.
        app_name: Name of the Modal app to stream logs from.
        check_interval: How often to check for completion (seconds).

    Returns:
        The result of the function execution.

    Raises:
        Exception: If the Modal function execution fails.
        KeyboardInterrupt: If the user cancels the execution.
    """
    logger.info(f"Starting {description}")

    # Get function call ID for filtering (if available)
    call_id = None
    try:
        call_id = getattr(function_call, "object_id", None)
        if call_id:
            logger.debug(f"Function call ID: {call_id}")
    except Exception:
        pass

    # Wait a moment for the function to start before beginning log streaming
    # This helps avoid capturing old logs from previous runs
    time.sleep(1)

    # Start log streaming in a separate thread
    log_stream_active = threading.Event()
    log_stream_active.set()
    start_time = time.time()

    def stream_logs() -> None:
        """Stream logs from Modal CLI in a separate thread."""
        try:
            # Use modal CLI to stream logs (automatically streams while app is active)
            cmd = [
                "modal",
                "app",
                "logs",
                app_name,
                "--timestamps",
            ]
            logger.debug(f"Starting log stream: {' '.join(cmd)}")

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,  # Line buffered
                universal_newlines=True,
            )

            # Stream logs line by line
            while log_stream_active.is_set() and process.poll() is None:
                if process.stdout:
                    line = process.stdout.readline()
                    if line:
                        # Clean up the log line and forward to our logger
                        log_msg = line.strip()

                        # Skip empty lines and "No logs" messages
                        if not log_msg or log_msg.startswith("No logs"):
                            continue

                        # Try to filter out old logs by checking if they contain our call ID
                        # or if they occurred after we started the function
                        current_time = time.time()
                        log_age = current_time - start_time

                        # Only show logs that are likely from the current execution
                        # Skip logs that seem to be from much earlier runs
                        if call_id and call_id in log_msg:
                            # This log definitely belongs to our execution
                            logger.info(f"{log_msg}")
                        elif (
                            log_age < 300
                        ):  # Only show logs from last 5 minutes
                            # This log is recent enough to likely be ours
                            logger.info(f"{log_msg}")
                        # Else: skip old logs

                else:
                    break

            # Clean up process
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()

        except FileNotFoundError:
            logger.warning(
                "Modal CLI not found. Install with: pip install modal"
            )
        except Exception as e:
            logger.debug(f"Log streaming error: {e}")

    # Start log streaming thread
    log_thread = threading.Thread(target=stream_logs, daemon=True)
    log_thread.start()

    try:
        # Poll for function completion
        start_time = time.time()
        while True:
            try:
                # Try to get result with timeout=0 (non-blocking)
                result = function_call.get(timeout=0)
                elapsed = time.time() - start_time
                logger.info(
                    f"{description} completed successfully after {elapsed:.1f}s"
                )
                return result
            except TimeoutError:
                # Function still running, continue waiting
                time.sleep(check_interval)
            except Exception as e:
                # Function failed
                elapsed = time.time() - start_time
                logger.error(f"{description} failed after {elapsed:.1f}s: {e}")
                raise

    except KeyboardInterrupt:
        logger.info(f"Cancelling {description}")
        try:
            function_call.cancel()
            logger.info("Function cancelled successfully")
        except Exception as cancel_error:
            logger.warning(f"Could not cancel function: {cancel_error}")
        raise
    finally:
        # Stop log streaming
        log_stream_active.clear()
        # Give the log thread a moment to clean up
        time.sleep(0.5)
