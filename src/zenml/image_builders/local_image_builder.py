#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""Local Docker image builder implementation."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from typing import TYPE_CHECKING, List, Optional, Type, cast

from pydantic import Field

from zenml.container_registries.base_container_registry import (
    BaseContainerRegistry,
)
from zenml.image_builders import (
    BaseImageBuilder,
    BaseImageBuilderConfig,
    BaseImageBuilderFlavor,
)
from zenml.logger import get_logger
from zenml.utils import docker_utils
from zenml.utils.enum_utils import StrEnum

if TYPE_CHECKING:
    from zenml.config.docker_settings import DockerBuildOptions
    from zenml.image_builders import BuildContext

logger = get_logger(__name__)


class LocalContainerRuntime(StrEnum):
    """Container engine used by the local image builder."""

    DOCKER = "docker"
    PODMAN = "podman"


class LocalImageBuilderConfig(BaseImageBuilderConfig):
    """Local image builder configuration."""

    use_subprocess_call: bool = Field(
        default=False,
        description="Whether to use a subprocess `docker build` call to "
        "build the image instead of using the Docker python SDK. Ignored when "
        "`container_runtime` is `podman` (Podman always uses the CLI).",
    )
    container_runtime: LocalContainerRuntime = Field(
        default=LocalContainerRuntime.DOCKER,
        description="Selects which local engine runs builds, tags, and pushes "
        "images for this stack component. Use `docker` for Docker Desktop or a "
        "standard Docker daemon. Use `podman` for rootless Podman on "
        "Linux or other environments where the Podman CLI should drive "
        "build/tag/push instead of docker.",
    )


class LocalImageBuilder(BaseImageBuilder):
    """Local image builder implementation."""

    @property
    def config(self) -> LocalImageBuilderConfig:
        """The stack component configuration.

        Returns:
            The configuration.
        """
        return cast(LocalImageBuilderConfig, self._config)

    @property
    def is_building_locally(self) -> bool:
        """Whether the image builder builds the images on the client machine.

        Returns:
            True if the image builder builds locally, False otherwise.
        """
        return True

    def _check_prerequisites(self) -> None:
        """Checks that all prerequisites are installed.

        Raises:
            RuntimeError: If any of the prerequisites are not installed or
                running.
        """
        if self.config.container_runtime == LocalContainerRuntime.PODMAN:
            if not shutil.which("podman"):
                raise RuntimeError(
                    "`podman` is required to run the local image builder."
                )
            return

        if not shutil.which("docker"):
            raise RuntimeError(
                "`docker` is required to run the local image builder."
            )

        if not docker_utils.check_docker():
            # For 3., this is not supported by the python docker library
            # https://github.com/docker/docker-py/issues/3146
            raise RuntimeError(
                "Unable to connect to the Docker daemon. There are three "
                "common causes for this:\n"
                "1) The Docker daemon isn't running.\n"
                "2) The Docker client isn't configured correctly. The client "
                "loads its configuration from the following file: "
                "$HOME/.docker/config.json. If your configuration file is in a "
                "different location, set the `DOCKER_CONFIG` environment "
                "variable to the directory that contains your `config.json` "
                "file.\n"
                "3) If your Docker CLI is working fine but you ran into this "
                "issue, you might be using a non-default Docker context which "
                "is not supported by the Docker python library. To verify "
                "this, run `docker context ls` and check which context has a "
                "`*` next to it. If this is not the `default` context, copy "
                "the `DOCKER ENDPOINT` value of that context and set the "
                "`DOCKER_HOST` environment variable to that value."
            )

    def build(
        self,
        image_name: str,
        build_context: "BuildContext",
        docker_build_options: Optional["DockerBuildOptions"] = None,
        container_registry: Optional["BaseContainerRegistry"] = None,
    ) -> str:
        """Builds and optionally pushes an image using the local engine.

        Args:
            image_name: Name of the image to build and push.
            build_context: The build context to use for the image.
            docker_build_options: Docker build options.
            container_registry: Optional container registry to push to.

        Returns:
            The Docker image repo digest.
        """
        self._check_prerequisites()

        if self.config.container_runtime == LocalContainerRuntime.PODMAN:
            self._build_with_container_cli(
                binary="podman",
                image_name=image_name,
                build_context=build_context,
                docker_build_options=docker_build_options,
            )
        elif self.config.use_subprocess_call:
            self._build_with_container_cli(
                binary="docker",
                image_name=image_name,
                build_context=build_context,
                docker_build_options=docker_build_options,
            )
        else:
            self._build_with_python_sdk(
                image_name=image_name,
                build_context=build_context,
                docker_build_options=docker_build_options,
                container_registry=container_registry,
            )

        if container_registry:
            return self.push_image(image_name, container_registry)
        return image_name

    def tag_image(self, source: str, target: str) -> None:
        """Tag a local image as ``target`` using the configured engine.

        Args:
            source: Existing local image reference.
            target: Full image name including tag to apply.


        Raises:
            RuntimeError: If the tag operation fails.
        """
        if self.config.container_runtime == LocalContainerRuntime.DOCKER:
            docker_utils.tag_image(source, target=target)
            return

        self._check_prerequisites()
        result = subprocess.run(
            ["podman", "tag", source, target],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"Podman tag failed: {result.stderr or result.stdout}"
            )

    def get_image_repo_digest(
        self,
        image_name: str,
    ) -> Optional[str]:
        """Get the repository digest of an image.

        Args:
            image_name: The name of the image.

        Returns:
            The repository digest of the image.
        """
        self._check_prerequisites()

        if self.config.container_runtime == LocalContainerRuntime.DOCKER:
            try:
                docker_client = docker_utils._try_get_docker_client_from_env()
                metadata = docker_client.images.get_registry_data(image_name)
            except Exception:
                return None

            return cast(str, metadata.id.split(":")[-1])

        return _podman_select_repo_digest(image_name)

    def is_image_local(self, image_name: str) -> bool:
        """Return True if the image exists locally without a single digest.

        Args:
            image_name: Image reference to inspect.

        Returns:
            Whether the image appears to be a local-only build.
        """
        if self.config.container_runtime == LocalContainerRuntime.DOCKER:
            return docker_utils.is_local_image(image_name)

        self._check_prerequisites()
        exists = subprocess.run(
            ["podman", "image", "exists", image_name],
            capture_output=True,
        )
        if exists.returncode != 0:
            return False
        digests = _podman_inspect_repo_digests(image_name)
        return len(digests) != 1

    def push_image(
        self,
        image_name: str,
        container_registry: "BaseContainerRegistry",
    ) -> str:
        """Push using Podman CLI or delegate to the default Docker path.

        Args:
            image_name: Full image reference including tag.
            container_registry: Registry to push to.

        Returns:
            Repository digest when available, otherwise the image name.
        """
        if not container_registry.is_valid_image_name_for_registry(image_name):
            raise ValueError(
                f"Docker image `{image_name}` does not belong to container "
                f"registry `{container_registry.config.uri}`."
            )

        container_registry.prepare_image_push(image_name)

        self._check_prerequisites()

        if self.config.container_runtime == LocalContainerRuntime.DOCKER:
            return docker_utils.push_image(
                image_name, docker_client=container_registry.docker_client
            )

        _podman_login_if_needed(container_registry)
        logger.info("Pushing container image `%s` via Podman.", image_name)
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
        digest = _podman_select_repo_digest(image_name)
        if digest is None:
            raise RuntimeError(
                f"Unable to find repo digest after pushing image {image_name}."
            )
        return digest

    def _build_with_python_sdk(
        self,
        image_name: str,
        build_context: "BuildContext",
        docker_build_options: Optional["DockerBuildOptions"] = None,
        container_registry: Optional["BaseContainerRegistry"] = None,
    ) -> None:
        """Builds an image using the Python Docker SDK.

        Args:
            image_name: Name of the image to build and push.
            build_context: The build context to use for the image.
            docker_build_options: Docker build options.
            container_registry: Optional container registry.
        """
        if container_registry:
            # Use the container registry's docker client, which may be
            # authenticated to access additional registries
            docker_client = container_registry.docker_client
        else:
            docker_client = docker_utils._try_get_docker_client_from_env()

        build_options = (
            docker_build_options.to_docker_python_sdk_options()
            if docker_build_options
            else {}
        )

        with tempfile.TemporaryFile(mode="w+b") as f:
            build_context.write_archive(f)

            # We use the client api directly here, so we can stream the logs
            f.seek(0)
            output_stream = docker_client.images.client.api.build(
                fileobj=f,
                custom_context=True,
                tag=image_name,
                **build_options,
            )
        docker_utils._process_stream(output_stream)

    def _build_with_container_cli(
        self,
        binary: str,
        image_name: str,
        build_context: "BuildContext",
        docker_build_options: Optional["DockerBuildOptions"] = None,
    ) -> None:
        """Builds an image using a subprocess ``docker``/``podman`` build call.

        Args:
            binary: Executable name (`docker` or `podman`).
            image_name: Name of the image to build.
            build_context: The build context to use for the image.
            docker_build_options: Docker-compatible CLI build options.

        Raises:
            RuntimeError: If the subprocess call fails.
        """
        with tempfile.TemporaryFile(mode="w+b") as f:
            build_context.write_archive(f)
            f.seek(0)

            # The `-` signals that the build context will be passed as a tar
            # file to stdin
            command = [binary, "build", "-", "-t", image_name]
            if docker_build_options:
                command.extend(docker_build_options.to_docker_cli_options())
            process = subprocess.Popen(command, stdin=f)
            result = process.wait()
            if result != 0:
                raise RuntimeError(
                    f"Failed to build image {image_name} with `{binary}`. "
                    "Please check the logs above for more information."
                )


def _podman_inspect_repo_digests(image_name: str) -> List[str]:
    """Return RepoDigests entries from `podman inspect`."""
    result = subprocess.run(
        ["podman", "inspect", image_name, "--format", "{{json .RepoDigests}}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return []
    raw = (result.stdout or "").strip() or "[]"
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    return [d for d in parsed if isinstance(d, str)]


def _podman_login_if_needed(container_registry: BaseContainerRegistry) -> None:
    """Run `podman login` when the registry stack component has credentials."""
    credentials = container_registry.credentials
    if not credentials:
        return
    username, password = credentials
    registry = container_registry.config.uri
    logger.info("Logging in to `%s` with Podman.", registry)
    proc = subprocess.run(
        [
            "podman",
            "login",
            registry,
            "--username",
            username,
            "--password-stdin",
        ],
        input=password,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"Podman login failed for {registry}: {proc.stderr or proc.stdout}"
        )


def _podman_select_repo_digest(image_name: str) -> Optional[str]:
    """Pick a repo digest for ``image_name`` after push (Podman)."""
    image_name_without_tag, _ = image_name.rsplit(":", maxsplit=1)
    digests = _podman_inspect_repo_digests(image_name)
    prefix_candidates = [f"{image_name_without_tag}@"]
    if image_name_without_tag.startswith(("index.docker.io/", "docker.io/")):
        without_index = image_name_without_tag.split("/", maxsplit=1)[1]
        prefix_candidates.append(f"{without_index}@")
    for digest in digests:
        if digest.startswith(tuple(prefix_candidates)):
            return digest
    for digest in reversed(digests):
        if "@" in digest:
            return digest
    return None


class LocalImageBuilderFlavor(BaseImageBuilderFlavor):
    """Local image builder flavor."""

    @property
    def name(self) -> str:
        """The flavor name.

        Returns:
            The flavor name.
        """
        return "local"

    @property
    def docs_url(self) -> Optional[str]:
        """A url to point at docs explaining this flavor.

        Returns:
            A flavor docs url.
        """
        return self.generate_default_docs_url()

    @property
    def sdk_docs_url(self) -> Optional[str]:
        """A url to point at docs explaining this flavor.

        Returns:
            A flavor docs url.
        """
        return self.generate_default_sdk_docs_url()

    @property
    def logo_url(self) -> str:
        """A url to represent the flavor in the dashboard.

        Returns:
            The flavor logo.
        """
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/image_builder/local.svg"

    @property
    def config_class(self) -> Type[LocalImageBuilderConfig]:
        """Config class.

        Returns:
            The config class.
        """
        return LocalImageBuilderConfig

    @property
    def implementation_class(self) -> Type[LocalImageBuilder]:
        """Implementation class.

        Returns:
            The implementation class.
        """
        return LocalImageBuilder
