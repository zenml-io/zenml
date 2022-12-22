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
from typing import TYPE_CHECKING, Any, Dict, Optional, Type, cast

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
        """Build context class to use.

        The default build context class creates a build context that works
        for the Docker daemon. Override this method if your image builder
        requires a custom context.

        Returns:
            The build context class.
        """
        from zenml.image_builders import BuildContext

        return BuildContext

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
