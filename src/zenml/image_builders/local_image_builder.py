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
from typing import TYPE_CHECKING, Type, cast

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

    @staticmethod
    def _check_prerequisites() -> None:
        """Checks that all prerequisites are installed.

        Raises:
            RuntimeError: If any of the prerequisites are not installed.
        """
        if not shutil.which("docker"):
            raise RuntimeError(
                "`docker` is required to run the local image builder."
            )

    def build(self, image_name: str, build_context: "BuildContext") -> None:
        docker_client = DockerClient.from_env()

        with tempfile.TemporaryFile(mode="w+b") as f:
            build_context.write_archive(f)

            # We use the client api directly here, so we can stream the logs
            output_stream = docker_client.images.client.api.build(
                fileobj=f,
                custom_context=True,
                tag=image_name,
                platform="linux/amd64",
                # **build_options,
            )
        docker_utils._process_stream(output_stream)

    def build_and_push(
        self,
        image_name: str,
        build_context: "BuildContext",
        container_registry: "BaseContainerRegistry",
    ) -> str:
        self.build(image_name=image_name, build_context=build_context)
        return container_registry.push_image(image_name)


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
