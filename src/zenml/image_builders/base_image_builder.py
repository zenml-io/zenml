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

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Type, cast

from zenml.enums import StackComponentType
from zenml.stack import Flavor, StackComponent
from zenml.stack.stack_component import StackComponentConfig

if TYPE_CHECKING:
    from zenml.container_registries import BaseContainerRegistry
    from zenml.image_builders import BuildContext


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
        from zenml.image_builders import BuildContext

        return BuildContext

    def build(self, image_name: str, build_context: "BuildContext") -> None:
        """Builds an image.

        Args:
            image_name: The name of the image to build.
            build_context: The build context to use for the image.

        Raises:
            NotImplementedError: If the image builder does not support the
                functionality of building images without pushing.
        """
        raise NotImplementedError(
            "Building without pushing is not supported for the "
            f"{self.__class__.__name__}."
        )

    @abstractmethod
    def build_and_push(
        self,
        image_name: str,
        build_context: "BuildContext",
        container_registry: "BaseContainerRegistry",
    ) -> str:
        """Builds and pushes a Docker image.

        Args:
            image_name: Name of the image to build and push.
            build_context: The build context to use for the image.
            container_registry: The container registry to push to.

        Returns:
            The Docker image repo digest.
        """


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
