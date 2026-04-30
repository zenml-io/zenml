#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""Abstract container engine for local OCI-compatible tooling."""

import re
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, List, Optional, Tuple

from zenml.enums import ContainerEngineType
from zenml.logger import get_logger
from zenml.utils import io_utils

if TYPE_CHECKING:
    from zenml.config.docker_settings import DockerBuildOptions
    from zenml.container_registries.base_container_registry import (
        BaseContainerRegistry,
    )
    from zenml.image_builders import BuildContext

logger = get_logger(__name__)


class ContainerEngine(ABC):
    """Client-side abstraction over Docker/Podman (build, tag, push, inspect).

    Implementations encapsulate OCI client details; callers use the factory
    functions in :mod:`zenml.container_engines.factory` for the active engine.
    """

    @property
    @abstractmethod
    def engine_type(self) -> ContainerEngineType:
        """The type of the container engine.

        Returns:
            The type of the container engine.
        """

    @abstractmethod
    def check_availability(self) -> Tuple[bool, str | None]:
        """Check whether this engine is installed and accessible and return the error message if not.

        Returns:
            ``True`` if the engine binary and runtime are likely available, else
            ``False`` and an error message if not.
        """

    @abstractmethod
    def login(
        self,
        username: str,
        password: str,
        registry: str,
    ) -> None:
        """Authenticate the container engine with the container registry credentials.

        Args:
            username: Registry username.
            password: Registry password or token.
            registry: Registry host or URI.
        """

    def login_registry(
        self, container_registry: "BaseContainerRegistry"
    ) -> None:
        """Authenticate the container engine with the container registry credentials.

        Args:
            container_registry: Container registry to authenticate with.
        """
        credentials = container_registry.credentials
        if credentials:
            username, password = credentials
            self.login(
                username=username,
                password=password,
                registry=container_registry.config.uri,
            )

    @abstractmethod
    def build(
        self,
        image_name: str,
        build_context: "BuildContext",
        docker_build_options: Optional["DockerBuildOptions"] = None,
        container_registry: Optional["BaseContainerRegistry"] = None,
        **kwargs: Any,
    ) -> None:
        """Build an image locally from a tarball build context.

        Args:
            image_name: Target image reference including tag.
            build_context: Archive and Dockerfile content for the build.
            docker_build_options: Optional Docker-compatible build options.
            container_registry: When set, registry credentials are applied for
                authenticated base-image pulls during the build.
            **kwargs: Additional keyword arguments.

        Returns:
            None

        Raises:
            RuntimeError: If the build fails (implementation-specific).
        """

    @abstractmethod
    def tag_image(self, source: str, target: str) -> None:
        """Apply an additional local name/tag to an existing local image.

        Args:
            source: Existing local image reference.
            target: New local reference (alias) for the same image.

        Returns:
            None

        Raises:
            RuntimeError: If the engine cannot apply the tag.
        """

    @abstractmethod
    def push_image(
        self,
        image_name: str,
        container_registry: Optional["BaseContainerRegistry"] = None,
    ) -> str:
        """Push a local image to the configured registry.

        Args:
            image_name: Full image reference including tag.
            container_registry: Container registry to push to. Used for
                validation and credentials, if provided.

        Returns:
            Repository digest when the engine reports one; otherwise an
            implementation-defined stable surrogate (e.g. unique tag).

        Raises:
            RuntimeError: If authentication or push fails.
        """

    @abstractmethod
    def is_image_local(self, image_name: str) -> bool:
        """Return whether the image appears to exist only locally.

        Args:
            image_name: Image reference to inspect.

        Returns:
            ``True`` if the image is present locally without a resolved remote
            repo digest heuristic; ``False`` otherwise.
        """

    @abstractmethod
    def get_image_repo_digest(
        self,
        image_name: str,
        container_registry: Optional["BaseContainerRegistry"] = None,
    ) -> Optional[str]:
        """Resolve the repository digest for an image when the client can.

        Args:
            image_name: Image reference (may include tag).
            container_registry: When set and the name matches the registry,
                credentials from this component are used for registry access.

        Returns:
            Repo digest string (e.g. ``sha256:...``) when resolvable, else
            ``None``.
        """

    @staticmethod
    def sanitize_tag(tag: str) -> str:
        """Sanitize a Docker tag.

        Args:
            tag: The tag to sanitize.

        Raises:
            ValueError: If the tag is empty.

        Returns:
            The sanitized tag.
        """
        tag = re.sub(r"[^a-zA-Z0-9_.\-]", "", tag)
        # Tags can not start with a dot or a dash
        tag = re.sub(r"^[-.]", "_", tag)

        if not tag:
            raise ValueError("Docker image tag cannot be empty.")

        return tag[:128]

    @staticmethod
    def parse_dockerignore(dockerignore_path: str) -> List[str]:
        """Parses a dockerignore file and returns a list of patterns to ignore.

        Args:
            dockerignore_path: Path to the dockerignore file.

        Returns:
            List of patterns to ignore.
        """
        try:
            file_content = io_utils.read_file_contents_as_string(
                dockerignore_path
            )
        except FileNotFoundError:
            logger.warning(
                "Unable to find dockerignore file at path '%s'.",
                dockerignore_path,
            )
            return []

        exclude_patterns = []
        for line in file_content.split("\n"):
            line = line.strip()
            if line and not line.startswith("#"):
                exclude_patterns.append(line)

        return exclude_patterns
