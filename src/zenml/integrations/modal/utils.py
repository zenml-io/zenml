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

import hashlib
import os
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
        """Return formatted error message with suggestions.

        Returns:
            Formatted error message, optionally with suggestions.
        """
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
        logger.info("Using platform token ID and secret from config")
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
        logger.info("Using platform token ID from config")
        logger.warning(
            "Only token ID provided. Make sure MODAL_TOKEN_SECRET is set "
            "or platform authentication may fail."
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
            "or platform authentication may fail."
        )
        logger.debug(f"Token secret starts with: {token_secret[:5]}...")

    else:
        logger.info("Using default platform authentication (~/.modal.toml)")
        # Check if default auth exists
        modal_toml_path = os.path.expanduser("~/.modal.toml")
        if os.path.exists(modal_toml_path):
            logger.debug(f"Found platform config at {modal_toml_path}")
        else:
            logger.warning(
                f"No platform config found at {modal_toml_path}. "
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
    gpu_count = resource_settings.gpu_count
    if gpu_count is None or gpu_count == 0:
        return gpu_type
    return f"{gpu_type}:{gpu_count}"


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


def _generate_image_cache_key(
    image_name: str, environment: Dict[str, str]
) -> str:
    """Generate a cache key for Modal image based on inputs.

    Args:
        image_name: Base Docker image name
        environment: Environment variables

    Returns:
        Hash string to use as cache key
    """
    # Create deterministic string from inputs
    cache_input = f"{image_name}|{sorted(environment.items())}"
    return hashlib.sha256(cache_input.encode()).hexdigest()[:12]


# Removed _get_cached_modal_image_name as we're using Modal's internal caching


def build_modal_image(
    image_name: str,
    stack: "Stack",
    environment: Dict[str, str],
) -> Any:
    """Build a Modal image from a ZenML-built Docker image with caching.

    Args:
        image_name: The name of the Docker image to use as base.
        stack: The ZenML stack containing container registry.
        environment: Environment variables to set in the image.
        force_rebuild: Force rebuilding even if cached image exists.

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

    # Generate cache key for this image configuration
    cache_key = _generate_image_cache_key(image_name, environment)

    logger.info(f"Building Modal image (cache key: {cache_key})")
    logger.info(f"Base image: {image_name}")

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
    # Modal will automatically cache layers and reuse when possible
    logger.info(f"Creating Modal image from base: {image_name}")
    zenml_image = (
        modal.Image.from_registry(image_name, secret=registry_secret)
        .pip_install("modal")  # Install Modal in the container
        .env(environment)
    )

    return zenml_image


def generate_sandbox_tags(
    pipeline_name: str,
    deployment_id: str,
    execution_mode: str,
    step_name: Optional[str] = None,
    run_id: Optional[str] = None,
) -> Dict[str, str]:
    """Generate tags for Modal sandboxes.

    Args:
        pipeline_name: Name of the pipeline
        deployment_id: ZenML deployment ID
        execution_mode: Execution mode (PIPELINE or PER_STEP)
        step_name: Step name (for PER_STEP mode)
        run_id: Pipeline run ID

    Returns:
        Dictionary of tags for the sandbox
    """
    tags = {
        "zenml_pipeline": pipeline_name,
        "zenml_deployment_id": deployment_id,
        "zenml_execution_mode": execution_mode,
        "zenml_component": "modal_orchestrator",
    }

    if step_name:
        tags["zenml_step"] = step_name

    if run_id:
        tags["zenml_run_id"] = run_id

    return tags


def create_modal_stack_validator() -> StackValidator:
    """Create a stack validator for Modal components.

    Returns:
        A StackValidator that ensures remote artifact store and container registry.
    """

    def _validate_remote_components(stack: "Stack") -> Tuple[bool, str]:
        if stack.artifact_store.config.is_local:
            return False, (
                "Serverless components run code remotely and "
                "need to write files into the artifact store, but the "
                f"artifact store `{stack.artifact_store.name}` of the "
                "active stack is local. Please ensure that your stack "
                "contains a remote artifact store when using serverless "
                "components."
            )

        container_registry = stack.container_registry
        assert container_registry is not None

        if container_registry.config.is_local:
            return False, (
                "Serverless components run code remotely and "
                "need to push/pull Docker images, but the "
                f"container registry `{container_registry.name}` of the "
                "active stack is local. Please ensure that your stack "
                "contains a remote container registry when using serverless "
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
        # Fallback to highest resource requirements across all steps
        if deployment.step_configurations:
            # Find step with highest resource requirements for modal execution
            max_cpu = 0
            max_memory = 0
            max_gpu = 0
            best_step_resources = ResourceSettings()

            for step_config in deployment.step_configurations.values():
                step_resources = step_config.config.resource_settings
                step_cpu = step_resources.cpu_count or 0
                step_memory = step_resources.get_memory() or 0
                step_gpu = step_resources.gpu_count or 0

                # Calculate resource "score" to find most demanding step
                resource_score = (
                    step_cpu + (step_memory / 1024) + (step_gpu * 10)
                )
                best_score = max_cpu + (max_memory / 1024) + (max_gpu * 10)

                if resource_score > best_score:
                    max_cpu = step_cpu
                    max_memory = step_memory
                    max_gpu = step_gpu
                    best_step_resources = step_resources

            logger.info(
                f"No pipeline-level resource settings found. Using highest resource "
                f"requirements from steps: {max_cpu} CPUs, {max_memory / 1024:.1f}GB memory, "
                f"{max_gpu} GPUs"
            )
            resource_settings = best_step_resources
        else:
            resource_settings = ResourceSettings()  # Default empty settings

    return resource_settings
