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
import tempfile
from typing import TYPE_CHECKING, Any, Dict, Optional, Type, cast

from docker.client import DockerClient

from zenml.image_builders import (
    BaseImageBuilder,
    BaseImageBuilderConfig,
    BaseImageBuilderFlavor,
)
from zenml.utils import docker_utils

if TYPE_CHECKING:
    from zenml.container_registries import BaseContainerRegistry
    from zenml.image_builders import BuildContext


class LocalImageBuilderConfig(BaseImageBuilderConfig):
    """Local image builder configuration."""


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
    def _check_prerequisites() -> None:
        """Checks that all prerequisites are installed.

        Raises:
            RuntimeError: If any of the prerequisites are not installed or
                running.
        """
        if not shutil.which("docker"):
            raise RuntimeError(
                "`docker` is required to run the local image builder."
            )

        if not docker_utils.check_docker():
            raise RuntimeError(
                "Unable to connect to the Docker daemon. There are two "
                "common causes for this:\n"
                "1) The Docker daemon isn't running.\n"
                "2) The Docker client isn't configured correctly. The client "
                "loads its configuration from the following file: "
                "$HOME/.docker/config.json. If your configuration file is in a "
                "different location, set it using the `DOCKER_CONFIG` "
                "environment variable."
            )

    def build(
        self,
        image_name: str,
        build_context: "BuildContext",
        docker_build_options: Optional[Dict[str, Any]] = None,
        container_registry: Optional["BaseContainerRegistry"] = None,
    ) -> str:
        """Builds and optionally pushes an image using the local Docker client.

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
            # Use the container registry's docker client, which may be
            # authenticated to access additional registries
            docker_client = container_registry.docker_client
        else:
            docker_client = DockerClient.from_env()

        with tempfile.TemporaryFile(mode="w+b") as f:
            build_context.write_archive(f)

            # We use the client api directly here, so we can stream the logs
            output_stream = docker_client.images.client.api.build(
                fileobj=f,
                custom_context=True,
                tag=image_name,
                **(docker_build_options or {}),
            )
        docker_utils._process_stream(output_stream)

        if container_registry:
            return container_registry.push_image(image_name)
        else:
            return image_name


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
