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

import shutil
import subprocess
import tempfile
import uuid
from typing import TYPE_CHECKING, Optional, Type, cast

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
from zenml.utils import docker_utils, podman_utils
from zenml.utils.enum_utils import StrEnum

if TYPE_CHECKING:
    from docker.client import DockerClient

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
        default=LocalContainerRuntime.PODMAN,
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

    @staticmethod
    def _get_docker_client(
        container_registry: BaseContainerRegistry | None = None,
        authenticate_cli: bool = True,
    ) -> "DockerClient":
        """Returns a Docker client for a container registry.

        Args:
            container_registry: The container registry to get the Docker client
                for. If not provided, a client will be created from the
                environment.
            authenticate_cli: Whether to authenticate the Docker CLI too.

        Returns:
            The Docker client.
        """
        if container_registry:
            credentials = container_registry.credentials
            if credentials:
                username, password = credentials

                if authenticate_cli:
                    # The reason callers might also need to configure the Docker
                    # CLI here is the following: When calling the login method
                    # on the python client, it stores the credentials in memory,
                    # but doesn't actually use them in future calls to push/pull
                    # images in case a credential store or credential helper is
                    # configured. If the cred store/helper contains
                    # invalid/expired credentials for the registry, these calls
                    # will fail.
                    # This solution is not ideal as we're now replacing
                    # potentially long-lived credentials in the cred store with
                    # our short lived ones, but the best we can do without
                    # modifying the docker library.
                    docker_utils.authenticate_docker_cli(
                        username=username,
                        password=password,
                        registry=container_registry.config.uri,
                    )

                return docker_utils.get_docker_client(
                    username=username,
                    password=password,
                    registry=container_registry.config.uri,
                )

        return docker_utils.get_docker_client()

    def _authenticate_local_cli(
        self, container_registry: BaseContainerRegistry
    ) -> None:
        """Authenticates the local container engine CLI to a container registry.

        Args:
            container_registry: The container registry to authenticate to.
        """
        credentials = container_registry.credentials
        if not credentials:
            return

        username, password = credentials

        if self.config.container_runtime == LocalContainerRuntime.DOCKER:
            docker_utils.authenticate_docker_cli(
                username=username,
                password=password,
                registry=container_registry.config.uri,
            )
        elif self.config.container_runtime == LocalContainerRuntime.PODMAN:
            podman_utils.authenticate_podman_cli(
                username=username,
                password=password,
                registry=container_registry.config.uri,
            )

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

    def _check_registry_image(
        self, image_name: str, container_registry: BaseContainerRegistry
    ) -> None:
        """Checks if the image is valid for the container registry.

        Args:
            image_name: The name of the image to check.
            container_registry: The container registry to check the image for.

        Raises:
            ValueError: If the image is not valid for the container registry.
        """
        if not container_registry.is_valid_image_name_for_registry(image_name):
            raise ValueError(
                f"Container image `{image_name}` does not belong to container "
                f"registry `{container_registry.config.uri}`."
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

        if container_registry:
            self._check_registry_image(image_name, container_registry)

            # Authenticate the local container engine CLI to the container
            # registry to also allow the build to pull images from the registry,
            # if necessary.
            self._authenticate_local_cli(container_registry)

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
            return self._push_image(image_name, container_registry)

        return image_name

    def tag_image(self, source: str, target: str) -> None:
        """Tag a local image as ``target`` using the configured engine.

        Args:
            source: Existing local image reference.
            target: Full image name including tag to apply.


        Raises:
            RuntimeError: If the tag operation fails.
        """
        self._check_prerequisites()

        if self.config.container_runtime == LocalContainerRuntime.DOCKER:
            docker_utils.tag_image(source, target=target)
            return

        podman_utils.tag_image(source, target)

    def get_image_repo_digest(
        self,
        image_name: str,
        container_registry: Optional["BaseContainerRegistry"] = None,
    ) -> Optional[str]:
        """Get the repository digest of an image.

        Args:
            image_name: The name of the image.
            container_registry: The container registry to get the digest from.

        Returns:
            The repository digest of the image.
        """
        self._check_prerequisites()

        if (
            container_registry
            and container_registry.is_valid_image_name_for_registry(image_name)
        ):
            # Authenticate the local container engine CLI to the container
            # registry
            self._authenticate_local_cli(container_registry)

        if self.config.container_runtime == LocalContainerRuntime.DOCKER:
            return docker_utils.get_image_repo_digest(
                image_name,
                docker_client=self._get_docker_client(container_registry),
            )

        # Podman is currently unable to report the correct remote repo digest
        # (see https://github.com/containers/podman/issues/14779). We return
        # None in this case.
        return None

    def is_image_local(self, image_name: str) -> bool:
        """Check if an image exists only locally (not in a remote registry).

        Args:
            image_name: Image reference to inspect on the local engine.

        Returns:
            Whether the image exists only locally (i.e. hasn't been pushed to or
            pulled from a remote registry).

        """
        self._check_prerequisites()

        if self.config.container_runtime == LocalContainerRuntime.DOCKER:
            return docker_utils.is_local_image(image_name)

        return podman_utils.is_local_image(image_name)

    def _push_image(
        self, image_name: str, container_registry: "BaseContainerRegistry"
    ) -> str:
        """Pushes an image using the Podman CLI.

        Args:
            image_name: Full image reference including tag.
            container_registry: Registry to push to.

        Returns:
            Repository digest when available, otherwise the image name.
        """
        container_registry.prepare_image_push(image_name)

        if self.config.container_runtime == LocalContainerRuntime.DOCKER:
            return docker_utils.push_image(
                image_name,
                self._get_docker_client(
                    container_registry, authenticate_cli=False
                ),
            )

        podman_utils.push_image(image_name)

        # Podman is currently unable to report the correct remote repo digest
        # (see https://github.com/containers/podman/issues/14779). We simulate
        # a unique repo digest by generating a random UUID and using it as
        # an additional tag.
        unique_tag = uuid.uuid4()
        image_name_without_tag, _ = image_name.rsplit(":", maxsplit=1)
        unique_image_name = f"{image_name_without_tag}:{unique_tag}"
        podman_utils.tag_image(image_name, unique_image_name)
        podman_utils.push_image(unique_image_name)
        return unique_image_name

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
        self._check_prerequisites()

        self._check_registry_image(image_name, container_registry)

        self._authenticate_local_cli(container_registry)

        return self._push_image(image_name, container_registry)

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
        docker_client = self._get_docker_client(
            container_registry, authenticate_cli=False
        )

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
