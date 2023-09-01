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
"""Base class for all ZenML image builders."""

import hashlib
import os
import tempfile
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, Optional, Type, cast

from zenml.client import Client
from zenml.enums import StackComponentType
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.stack import Flavor, StackComponent
from zenml.stack.stack_component import StackComponentConfig

if TYPE_CHECKING:
    from zenml.container_registries import BaseContainerRegistry
    from zenml.image_builders import BuildContext

logger = get_logger(__name__)


class BaseImageBuilderConfig(StackComponentConfig):
    """Base config for image builders."""


class BaseImageBuilder(StackComponent, ABC):
    """Base class for all ZenML image builders."""

    @property
    def config(self) -> BaseImageBuilderConfig:
        """The stack component configuration.

        Returns:
            The configuration.
        """
        return cast(BaseImageBuilderConfig, self._config)

    @property
    def build_context_class(self) -> Type["BuildContext"]:
        """Build context class to use.

        The default build context class creates a build context that works
        for the Docker daemon. Override this method if your image builder
        requires a custom context.

        Returns:
            The build context class.
        """
        from zenml.image_builders import BuildContext

        return BuildContext

    @property
    @abstractmethod
    def is_building_locally(self) -> bool:
        """Whether the image builder builds the images on the client machine.

        Returns:
            True if the image builder builds locally, False otherwise.
        """

    @abstractmethod
    def build(
        self,
        image_name: str,
        build_context: "BuildContext",
        docker_build_options: Dict[str, Any],
        container_registry: Optional["BaseContainerRegistry"] = None,
    ) -> str:
        """Builds a Docker image.

        If a container registry is passed, the image will be pushed to that
        registry.

        Args:
            image_name: Name of the image to build.
            build_context: The build context to use for the image.
            docker_build_options: Docker build options.
            container_registry: Optional container registry to push to.

        Returns:
            The Docker image repo digest or name.
        """

    @staticmethod
    def _upload_build_context(
        build_context: "BuildContext",
        parent_path_directory_name: str,
    ) -> str:
        """Uploads a Docker image build context to a remote location.

        Args:
            build_context: The build context to upload.
            parent_path_directory_name: The name of the directory to upload
                the build context to. It will be appended to the artifact
                store path to create the parent path where the build context
                will be uploaded to.

        Returns:
            The path to the uploaded build context.
        """
        artifact_store = Client().active_stack.artifact_store
        parent_path = f"{artifact_store.path}/{parent_path_directory_name}"
        fileio.makedirs(parent_path)

        hash_ = hashlib.sha1()  # nosec
        with tempfile.NamedTemporaryFile(mode="w+b", delete=False) as f:
            build_context.write_archive(f, gzip=True)

            while True:
                data = f.read(64 * 1024)
                if not data:
                    break
                hash_.update(data)

            filename = f"{hash_.hexdigest()}.tar.gz"
            filepath = f"{parent_path}/{filename}"
            if not fileio.exists(filepath):
                logger.info("Uploading build context to `%s`.", filepath)
                fileio.copy(f.name, filepath)
            else:
                logger.info("Build context already exists, not uploading.")

        os.unlink(f.name)
        return filepath


class BaseImageBuilderFlavor(Flavor, ABC):
    """Base class for all ZenML image builder flavors."""

    @property
    def type(self) -> StackComponentType:
        """Returns the flavor type.

        Returns:
            The flavor type.
        """
        return StackComponentType.IMAGE_BUILDER

    @property
    def config_class(self) -> Type[BaseImageBuilderConfig]:
        """Config class.

        Returns:
            The config class.
        """
        return BaseImageBuilderConfig

    @property
    def implementation_class(self) -> Type[BaseImageBuilder]:
        """Implementation class.

        Returns:
            The implementation class.
        """
        return BaseImageBuilder
