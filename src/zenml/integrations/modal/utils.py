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
from typing import Dict, List, Optional, Tuple

import modal

from zenml.enums import StackComponentType
from zenml.logger import get_logger
from zenml.stack import Stack, StackValidator

logger = get_logger(__name__)

MODAL_TOKEN_ID_ENV = "MODAL_TOKEN_ID"
MODAL_TOKEN_SECRET_ENV = "MODAL_TOKEN_SECRET"
MODAL_WORKSPACE_ENV = "MODAL_WORKSPACE"
MODAL_ENVIRONMENT_ENV = "MODAL_ENVIRONMENT"
MODAL_CONFIG_PATH = os.path.expanduser("~/.modal.toml")


def _validate_token_prefix(
    value: str, expected_prefix: str, label: str
) -> None:
    """Warn if a credential doesn't match Modal's expected prefix.

    This helps catch misconfigurations early without logging secret content.
    """
    if not value.startswith(expected_prefix):
        logger.warning(
            f"{label} format may be invalid. Expected prefix: {expected_prefix}"
        )


def _set_env_if_present(var_name: str, value: Optional[str]) -> bool:
    """Set an environment variable only if a non-empty value is provided.

    Returns:
        True if the environment variable was set, False otherwise.
    """
    if value is None or value == "":
        return False
    os.environ[var_name] = value
    return True


def setup_modal_client(
    token_id: Optional[str] = None,
    token_secret: Optional[str] = None,
    workspace: Optional[str] = None,
    environment: Optional[str] = None,
) -> None:
    """Setup Modal client authentication and context.

    Precedence for credentials:
      1) Explicit arguments (token_id, token_secret)
      2) Existing environment variables (MODAL_TOKEN_ID, MODAL_TOKEN_SECRET)
      3) Default Modal configuration (~/.modal.toml)

    Notes:
    - The 'environment' parameter refers to the Modal environment name (e.g., 'main'),
      not a dict of process environment variables.
    - This function avoids logging secret values. Validation only checks known prefixes.

    Args:
        token_id: Modal API token ID (ak-xxxxx format).
        token_secret: Modal API token secret (as-xxxxx format).
        workspace: Modal workspace name.
        environment: Modal environment name.
    """
    # Remember whether values came from args vs. env to improve diagnostics without leaking secrets.
    arg_token_id = token_id
    arg_token_secret = token_secret

    # Coalesce from env if not explicitly provided. This reduces friction if users
    # supply one value via configuration and the other via environment.
    token_id = token_id or os.environ.get(MODAL_TOKEN_ID_ENV)
    token_secret = token_secret or os.environ.get(MODAL_TOKEN_SECRET_ENV)

    tokens_provided = []
    token_sources: Dict[str, str] = {}

    if token_id:
        _validate_token_prefix(token_id, "ak-", "Token ID")
        _set_env_if_present(MODAL_TOKEN_ID_ENV, token_id)
        tokens_provided.append("ID")
        token_sources["ID"] = "args" if arg_token_id else "env"

    if token_secret:
        _validate_token_prefix(token_secret, "as-", "Token secret")
        _set_env_if_present(MODAL_TOKEN_SECRET_ENV, token_secret)
        tokens_provided.append("secret")
        token_sources["secret"] = "args" if arg_token_secret else "env"

    if tokens_provided:
        if len(tokens_provided) == 1:
            logger.warning(
                f"Only token {tokens_provided[0]} provided. Ensure both are set."
            )
        source_parts: List[str] = []
        if "ID" in token_sources:
            source_parts.append(f"ID from {token_sources['ID']}")
        if "secret" in token_sources:
            source_parts.append(f"secret from {token_sources['secret']}")
        source_summary = (
            " and ".join(source_parts) if source_parts else "args/env"
        )
        logger.debug(f"Using Modal API tokens ({source_summary}).")
    else:
        # Fall back to default Modal CLI auth configuration.
        logger.debug("Using default platform authentication (~/.modal.toml)")
        if os.path.exists(MODAL_CONFIG_PATH):
            logger.debug(f"Found platform config at {MODAL_CONFIG_PATH}")
        else:
            logger.warning(
                f"No platform config found at {MODAL_CONFIG_PATH}. "
                "Run 'modal token new' to set up authentication."
            )

    # Configure Modal workspace/environment context if provided.
    if workspace:
        _set_env_if_present(MODAL_WORKSPACE_ENV, workspace)
    if environment:
        _set_env_if_present(MODAL_ENVIRONMENT_ENV, environment)


def build_modal_image(
    image_name: str,
    stack: "Stack",
    environment: Optional[Dict[str, str]] = None,
) -> modal.Image:
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
    """
    if not stack.container_registry:
        raise RuntimeError(
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

    try:
        registry_secret = modal.Secret.from_dict(
            {
                "REGISTRY_USERNAME": docker_username,
                "REGISTRY_PASSWORD": docker_password,
            }
        )
    except Exception as e:
        raise RuntimeError(
            "Failed to create Modal secret for container registry credentials. "
            "Action required: verify your container registry credentials in the active ZenML stack and "
            "ensure your Modal account has permission to create secrets."
        ) from e

    try:
        modal_image = modal.Image.from_registry(
            image_name, secret=registry_secret
        ).pip_install("modal")
    except Exception as e:
        raise RuntimeError(
            "Failed to construct a Modal image from the specified Docker base image. "
            "Action required: ensure the image exists and is accessible from your container registry, "
            "and that the provided credentials are correct."
        ) from e

    if environment:
        try:
            modal_image = modal_image.env(environment)
        except Exception as e:
            # This is a defensive guard; env composition is local, but we still provide guidance.
            raise RuntimeError(
                "Failed to apply environment variables to the Modal image. "
                "Action required: verify that environment variable keys and values are valid strings."
            ) from e

    return modal_image


def get_modal_stack_validator() -> StackValidator:
    """Get a stack validator for Modal components.

    The validator ensures that the stack contains a remote artifact store and
    container registry.

    Returns:
        A stack validator for modal components.
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
