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
    Any,
    Dict,
    List,
    Optional,
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


def push_image(image_name: str) -> str:
    """Pushes an image to a container registry.

    Args:
        image_name: The full name (including a tag) of the image to push.

    Returns:
        The Docker repository digest of the pushed image.

    Raises:
        RuntimeError: If fetching the repository digest of the image failed.
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

    digest = get_image_repo_digest(image_name)
    if digest is None:
        raise RuntimeError(
            f"Unable to find repo digest after pushing image {image_name}."
        )
    return digest


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


def get_image_repo_digest(
    image_name: str,
) -> Optional[str]:
    """Gets the repository digest SHA-256 of an image.

    Uses ``podman manifest inspect`` JSON only. The digest comes from a
    manifest list with exactly one entry (not from local ``RepoDigests``).

    Args:
        image_name: Name of the image to get the digest for.

    Returns:
        The SHA-256 hex digest (without the ``sha256:`` prefix) when inspect
        reports exactly one manifest entry; otherwise ``None``.
    """
    result = subprocess.run(
        ["podman", "manifest", "inspect", image_name],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        logger.debug(
            "Podman manifest inspect failed for '%s': %s",
            image_name,
            (result.stderr or result.stdout or "").strip(),
        )
        return None

    try:
        data: Dict[str, Any] = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        logger.error(
            "Failed to parse podman manifest inspect JSON for '%s': %s",
            image_name,
            e,
        )
        return None

    manifests_raw = data.get("manifests")
    if not isinstance(manifests_raw, list):
        return None
    if len(manifests_raw) != 1:
        logger.debug(
            "Expected exactly one manifest entry for '%s', found %s",
            image_name,
            len(manifests_raw),
        )
        return None

    first = manifests_raw[0]
    if not isinstance(first, dict):
        return None
    digest_val = first.get("digest")
    if not isinstance(digest_val, str) or not digest_val.startswith("sha256:"):
        return None

    return digest_val.split(":", maxsplit=1)[-1]


def is_local_image(image_name: str) -> bool:
    """Returns whether an image was pulled from a registry or not.

    Args:
        image_name: Name of the image to check.

    Returns:
        `True` if the image was pulled from a registry, `False` otherwise.
    """
    exists = subprocess.run(
        ["podman", "image", "exists", image_name],
        capture_output=True,
    )
    if exists.returncode != 0:
        return False

    # An image with this name is available locally -> now check whether it
    # was pulled from a repo or built locally (in which case the repo
    # digest is empty)
    result = subprocess.run(
        ["podman", "image", "inspect", image_name],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        logger.error(f"Podman image inspect failed for '{image_name}'.")
        return False

    try:
        inspected: List[Dict[str, Any]] = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        logger.error(
            f"Failed to parse podman image inspect JSON for '{image_name}': {e}",
        )
        return False

    if not inspected:
        logger.debug(
            f"Podman image inspect returned no data for '{image_name}'."
        )
        return False

    repo_digests_raw = inspected[0].get("RepoDigests")
    repo_digests: List[str] = (
        repo_digests_raw if isinstance(repo_digests_raw, list) else []
    )

    # Prune localhost digests
    repo_digests = [
        digest
        for digest in repo_digests
        if not digest.startswith("localhost/")
    ]

    return len(repo_digests) == 0
