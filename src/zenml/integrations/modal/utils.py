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
from typing import Dict, Optional, Tuple

import modal

from zenml.enums import StackComponentType
from zenml.logger import get_logger
from zenml.stack import Stack, StackValidator

logger = get_logger(__name__)


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

        os.environ["MODAL_TOKEN_ID"] = token_id
        os.environ["MODAL_TOKEN_SECRET"] = token_secret
        logger.debug("Using platform token ID and secret from config")
        logger.debug(f"Token ID starts with: {token_id[:5]}...")
        logger.debug(f"Token secret starts with: {token_secret[:5]}...")

    elif token_id:
        if not token_id.startswith("ak-"):
            logger.warning(
                f"Token ID format may be invalid. Expected format: ak-xxxxx, "
                f"got: {token_id[:10]}... (truncated for security)"
            )

        os.environ["MODAL_TOKEN_ID"] = token_id
        logger.debug("Using platform token ID from config")
        logger.warning(
            "Only token ID provided. Make sure MODAL_TOKEN_SECRET is set "
            "or platform authentication may fail."
        )
        logger.debug(f"Token ID starts with: {token_id[:5]}...")

    elif token_secret:
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
        modal_toml_path = os.path.expanduser("~/.modal.toml")
        if os.path.exists(modal_toml_path):
            logger.debug(f"Found platform config at {modal_toml_path}")
        else:
            logger.warning(
                f"No platform config found at {modal_toml_path}. "
                "Run 'modal token new' to set up authentication."
            )

    if workspace:
        os.environ["MODAL_WORKSPACE"] = workspace
    if environment:
        os.environ["MODAL_ENVIRONMENT"] = environment


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

    registry_secret = modal.Secret.from_dict(
        {
            "REGISTRY_USERNAME": docker_username,
            "REGISTRY_PASSWORD": docker_password,
        }
    )

    modal_image = modal.Image.from_registry(
        image_name, secret=registry_secret
    ).pip_install("modal")

    if environment:
        modal_image = modal_image.env(environment)

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
