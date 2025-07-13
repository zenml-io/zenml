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
from typing import Any, Dict, List, Optional, Tuple, Union

import modal

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
        logger.debug("Using platform token ID and secret from config")
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
        logger.debug("Using platform token ID from config")
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
        logger.debug("Using default platform authentication (~/.modal.toml)")
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

    This function unifies GPU configuration from both Modal orchestrator settings
    and ResourceSettings. It prioritizes explicit GPU type from Modal settings,
    but falls back to ResourceSettings for GPU count and type.

    Args:
        gpu_type: The GPU type from Modal settings (e.g., "T4", "A100").
        resource_settings: The resource settings containing GPU configuration.

    Returns:
        The GPU string for Modal API, or None if no GPU requested.
        Format: "GPU_TYPE" or "GPU_TYPE:COUNT"
    """
    # Check if GPU is requested via ResourceSettings
    gpu_count = resource_settings.gpu_count

    # No GPU requested if no type specified
    if not gpu_type:
        return None

    # No GPU requested if count is explicitly 0
    if gpu_count == 0:
        return None

    # GPU type specified but no count, return just the type
    if gpu_count is None:
        return gpu_type

    # Both type and count specified
    return f"{gpu_type}:{gpu_count}"


def get_resource_values(
    resource_settings: ResourceSettings,
) -> Tuple[Optional[int], Optional[int]]:
    """Get CPU and memory values from resource settings with validation.

    Args:
        resource_settings: The resource settings.

    Returns:
        Tuple of (cpu_count, memory_mb) with validated values.
    """
    # Get CPU count with validation
    cpu_count: Optional[int] = None
    if resource_settings.cpu_count is not None:
        cpu_count = int(resource_settings.cpu_count)
        # Validate CPU count is reasonable
        if cpu_count <= 0:
            logger.warning(f"Invalid CPU count {cpu_count}, ignoring.")
            cpu_count = None
        elif cpu_count > 96:  # Modal's typical max
            logger.warning(
                f"CPU count {cpu_count} is very high. "
                "Consider if this is intentional."
            )

    # Convert memory to MB if needed with validation
    memory_mb: Optional[int] = None
    if resource_settings.memory:
        try:
            memory_value = resource_settings.get_memory(ByteUnit.MB)
            if memory_value is not None:
                memory_mb = int(memory_value)
                # Validate memory is reasonable
                if memory_mb <= 0:
                    logger.warning(f"Invalid memory {memory_mb}MB, ignoring.")
                    memory_mb = None
                elif memory_mb < 128:  # Less than 128MB seems too low
                    logger.warning(
                        f"Memory {memory_mb}MB is very low. "
                        "Consider if this is intentional."
                    )
                elif memory_mb > 1024 * 1024:  # More than 1TB seems high
                    logger.warning(
                        f"Memory {memory_mb}MB is very high. "
                        "Consider if this is intentional."
                    )
        except Exception as e:
            logger.warning(f"Failed to parse memory setting: {e}")
            memory_mb = None

    return cpu_count, memory_mb


def _build_modal_image_from_registry(
    image_name: str,
    stack: "Stack",
    environment: Optional[Dict[str, str]] = None,
) -> Any:
    """Build a Modal image from a Docker registry with authentication.

    This helper function centralizes the shared logic for building Modal images
    from Docker registries, including credential validation, secret creation,
    and image building with Modal installation.

    Args:
        image_name: The name of the Docker image to use as base.
        stack: The ZenML stack containing container registry.
        environment: Optional environment variables to apply to the image.

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

    logger.debug("Building new Modal image")
    logger.debug(f"Base image: {image_name}")

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
    logger.debug(f"Building Modal image from base: {image_name}")
    logger.debug(f"Creating Modal image from base: {image_name}")
    zenml_image = (
        modal.Image.from_registry(
            image_name, secret=registry_secret
        ).pip_install("modal")  # Install Modal in the container
    )

    # Apply environment variables if provided
    if environment:
        zenml_image = zenml_image.env(environment)

    return zenml_image


def get_or_build_modal_image(
    image_name: str,
    stack: "Stack",
    pipeline_name: str,
    build_id: str,
    app: Any,
) -> Any:
    """Get existing Modal image or build new one based on pipeline name and build ID.

    Args:
        image_name: The name of the Docker image to use as base.
        stack: The ZenML stack containing container registry.
        pipeline_name: The pipeline name for caching.
        build_id: The build ID for the image key.
        app: The Modal app to store/retrieve images.

    Returns:
        The configured Modal image.
    """
    # Try to get existing image from the app
    image_name_key = f"zenml_image_{build_id}"

    try:
        # Try to get stored image ID
        stored_id = modal.Dict.from_name(f"zenml-image-cache-{pipeline_name}")
        if image_name_key in stored_id:
            image_id = stored_id[image_name_key]
            existing_image = modal.Image.from_id(image_id)
            logger.debug(
                f"Using cached Modal image for build {build_id} in pipeline {pipeline_name}"
            )
            return existing_image
    except (modal.exceptions.NotFoundError, KeyError):
        # Dict doesn't exist or image not found, will build new one
        pass

    # Build new image using shared helper
    zenml_image = _build_modal_image_from_registry(
        image_name=image_name,
        stack=stack,
        environment=None,  # No environment variables for cached images
    )

    # Store the image in the app for future use
    setattr(app, image_name_key, zenml_image)

    return zenml_image


def build_modal_image(
    image_name: str,
    stack: "Stack",
    environment: Optional[Dict[str, str]] = None,
) -> Any:
    """Build a Modal image from a ZenML-built Docker image.

    Args:
        image_name: The name of the Docker image to use as base.
        stack: The ZenML stack containing container registry.
        environment: The environment variables to pass to the image.

    Returns:
        The configured Modal image.
    """
    # Use shared helper for image building
    return _build_modal_image_from_registry(
        image_name=image_name,
        stack=stack,
        environment=environment,
    )


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
        # No explicit pipeline resources: use sane defaults (ignore step-level)
        # As per user request: for pipeline mode, do not fallback to max(step resources)
        resource_settings = ResourceSettings(
            cpu_count=1,
            memory="1024MB",
            gpu_count=0,
        )
        logger.debug(
            "No explicit pipeline-level resource settings found. "
            "Using sane defaults: %s CPU, %s memory, %s GPU",
            resource_settings.cpu_count,
            resource_settings.memory,
            resource_settings.gpu_count,
        )
    return resource_settings
