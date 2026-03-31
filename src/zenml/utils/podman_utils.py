#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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
"""Utility functions relating to Docker."""

import json
import subprocess
from typing import (
    List,
)

from zenml.exceptions import AuthorizationException
from zenml.logger import get_logger

logger = get_logger(__name__)


def authenticate_podman_cli(
    username: str, password: str, registry: str
) -> None:
    """Run `podman login` to authenticate to a container registry.

    Args:
        username: The username to authenticate with.
        password: The password to authenticate with.
        registry: The registry to authenticate to.

    Raises:
        RuntimeError: If the login fails.
    """
    try:
        subprocess.run(
            [
                "podman",
                "login",
                registry,
                "--username",
                username,
                "--password-stdin",
            ],
            input=password.encode(),
            check=True,
        )
    except subprocess.CalledProcessError as e:
        raise AuthorizationException(
            f"Podman login failed for {registry}: {e}"
        ) from e


def push_image(image_name: str) -> None:
    """Pushes an image to a container registry.

    Args:
        image_name: The full name (including a tag) of the image to push.
    """
    logger.info(f"Pushing container image `{image_name}` via Podman.")
    push_result = subprocess.run(
        ["podman", "push", image_name],
        capture_output=True,
        text=True,
    )
    if push_result.returncode != 0:
        raise RuntimeError(
            f"Podman push failed: {push_result.stderr or push_result.stdout}"
        )
    logger.info("Finished pushing container image via Podman.")


def tag_image(image_name: str, target: str) -> None:
    """Tags an image.

    Args:
        image_name: The name of the image to tag.
        target: The full target name including a tag.

    Raises:
        RuntimeError: If the tag operation fails.
    """
    try:
        subprocess.run(
            ["podman", "tag", image_name, target],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Podman tag failed for {image_name}: {e}") from e


def is_local_image(image_name: str) -> bool:
    """Check if an image exists only locally (not in a remote registry).

    Args:
        image_name: Image reference to inspect.

    Returns:
        Whether the image exists only locally (i.e. hasn't been pushed to or
        pulled from a remote registry).
    """
    repo_digests = get_image_local_digests(image_name)

    # Prune localhost digests
    repo_digests = [
        digest
        for digest in repo_digests
        if not digest.startswith("localhost/")
    ]

    return len(repo_digests) == 0


def get_image_local_digests(
    image_name: str,
) -> List[str]:
    """Get the local digests of an image.

    Args:
        image_name: Image reference to inspect.

    Returns:
        The local digests of the image.
    """
    result = subprocess.run(
        [
            "podman",
            "image",
            "inspect",
            image_name,
            "--format",
            "{{json .RepoDigests}}",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        logger.error(f"Podman image inspect failed for '{image_name}'.")
        return []

    try:
        repo_digests: List[str] = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        logger.error(
            f"Failed to parse podman image inspect JSON for '{image_name}': {e}",
        )
        return []

    return repo_digests
