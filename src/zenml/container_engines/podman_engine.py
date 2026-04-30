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
"""Podman-backed :class:`ContainerEngine` implementation."""

import json
import shutil
import subprocess
import tempfile
import uuid
from typing import TYPE_CHECKING, Any, List, Optional, Tuple

from zenml.container_engines import ContainerEngine
from zenml.enums import ContainerEngineType
from zenml.exceptions import AuthorizationException
from zenml.logger import get_logger

if TYPE_CHECKING:
    from zenml.config.docker_settings import DockerBuildOptions
    from zenml.container_registries.base_container_registry import (
        BaseContainerRegistry,
    )
    from zenml.image_builders import BuildContext

logger = get_logger(__name__)


class PodmanContainerEngine(ContainerEngine):
    """Container engine using the Podman CLI."""

    @property
    def engine_type(self) -> ContainerEngineType:
        """The type of the container engine.

        Returns:
            The type of the container engine.
        """
        return ContainerEngineType.PODMAN

    def check_availability(self) -> Tuple[bool, str | None]:
        """Check whether this engine is installed and accessible and return the error message if not.

        Returns:
            ``True`` if the engine binary and runtime are likely available, else
            ``False`` and an error message if not.
        """
        if not shutil.which("podman"):
            return (
                False,
                "`podman` is not installed or not accessible on your system.",
            )

        result = subprocess.run(
            ["podman", "info"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return (
                False,
                "Podman is installed but `podman info` failed: "
                f"{result.stderr or result.stdout}",
            )

        return (True, None)

    def login(
        self,
        username: str,
        password: str,
        registry: str,
    ) -> None:
        """Run ``podman login`` for the given registry.

        Args:
            username: Registry username.
            password: Registry password or token.
            registry: Registry host or URI.

        Raises:
            AuthorizationException: If ``podman login`` fails.
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

    def build(
        self,
        image_name: str,
        build_context: "BuildContext",
        docker_build_options: Optional["DockerBuildOptions"] = None,
        container_registry: Optional["BaseContainerRegistry"] = None,
        **kwargs: Any,
    ) -> None:
        """Build an image using ``podman build`` with a tar context on stdin.

        Args:
            image_name: ``-t`` tag for the built image.
            build_context: Tarball written to build stdin.
            docker_build_options: Optional flags (Docker CLI compatible).
            container_registry: When set, runs ``podman login`` if creds exist.
            **kwargs: Additional keyword arguments.

        Raises:
            RuntimeError: If ``podman build`` exits non-zero.
        """
        if container_registry:
            self.login_registry(container_registry)

        with tempfile.TemporaryFile(mode="w+b") as f:
            build_context.write_archive(f)
            f.seek(0)
            command = ["podman", "build", "-", "-t", image_name]
            if docker_build_options:
                command.extend(docker_build_options.to_docker_cli_options())
            process = subprocess.Popen(command, stdin=f)
            result = process.wait()
            if result != 0:
                raise RuntimeError(
                    f"Failed to build image {image_name} with `podman`. "
                    "Please check the logs above for more information."
                )

    def tag_image(self, source: str, target: str) -> None:
        """Apply a local tag using Podman.

        Args:
            source: Existing image reference.
            target: Additional name:tag for the same image.

        Raises:
            RuntimeError: If ``podman tag`` fails.
        """
        try:
            subprocess.run(
                ["podman", "tag", source, target],
                check=True,
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Podman tag failed for {source}: {e}") from e

    def _push_image_cli(self, name: str) -> None:
        """Push ``name`` with ``podman push``.

        Args:
            name: Full image reference including tag.

        Raises:
            RuntimeError: If ``podman push`` exits non-zero.
        """
        logger.info("Pushing container image `%s` via Podman.", name)
        push_result = subprocess.run(
            ["podman", "push", name],
            capture_output=True,
            text=True,
        )
        if push_result.returncode != 0:
            raise RuntimeError(
                "Podman push failed: "
                f"{push_result.stderr or push_result.stdout}"
            )
        logger.info("Finished pushing container image via Podman.")

    def push_image(
        self,
        image_name: str,
        container_registry: Optional["BaseContainerRegistry"] = None,
    ) -> str:
        """Push an image and return a surrogate reference when digest is absent.

        Podman may not report a correct remote manifest digest; this method
        pushes a uniquely tagged image and returns that reference as a stable
        surrogate (see https://github.com/containers/podman/issues/14779).

        Args:
            image_name: Local image to push.
            container_registry: Container registry to push to. Used for
                validation and credentials, if provided.

        Returns:
            A unique image reference string used as the push identity.
        """
        if (
            container_registry
            and container_registry.is_valid_image_name_for_registry(image_name)
        ):
            self.login_registry(container_registry)
            container_registry.prepare_image_push(image_name)

        self._push_image_cli(image_name)

        unique_tag = uuid.uuid4()
        image_name_without_tag, _ = image_name.rsplit(":", maxsplit=1)
        unique_image_name = f"{image_name_without_tag}:{unique_tag}"
        self.tag_image(image_name, unique_image_name)
        self._push_image_cli(unique_image_name)
        return unique_image_name

    def is_image_local(self, image_name: str) -> bool:
        """Return whether Podman considers the image local-only.

        Args:
            image_name: Image reference to inspect.

        Returns:
            ``True`` if the image matches the local-only heuristic.
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
            logger.error("Podman image inspect failed for '%s'.", image_name)
            return False

        try:
            repo_digests: List[str] = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            logger.error(
                "Failed to parse podman image inspect JSON for '%s': %s",
                image_name,
                e,
            )
            return False

        repo_digests = [
            digest
            for digest in repo_digests
            if not digest.startswith("localhost/")
        ]

        return len(repo_digests) == 0

    def get_image_repo_digest(
        self,
        image_name: str,
        container_registry: Optional["BaseContainerRegistry"] = None,
    ) -> Optional[str]:
        """Always return ``None``; Podman cannot reliably report repo digests.

        Args:
            image_name: Unused; accepted for API symmetry.
            container_registry: Unused; accepted for API symmetry.

        Returns:
            ``None`` because remote manifest digests are not reliable for this
            engine (https://github.com/containers/podman/issues/14779).
        """
        return None
