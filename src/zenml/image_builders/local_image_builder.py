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

from typing import TYPE_CHECKING, Optional, Type, cast

from pydantic import Field

from zenml.container_engines import get_container_engine
from zenml.container_registries.base_container_registry import (
    BaseContainerRegistry,
)
from zenml.image_builders import (
    BaseImageBuilder,
    BaseImageBuilderConfig,
    BaseImageBuilderFlavor,
)

if TYPE_CHECKING:
    from zenml.config.docker_settings import DockerBuildOptions
    from zenml.image_builders import BuildContext


class LocalImageBuilderConfig(BaseImageBuilderConfig):
    """Local image builder configuration."""

    use_subprocess_call: bool = Field(
        default=False,
        description="Whether to use a subprocess `docker build` call to "
        "build the image instead of using the Docker python SDK. Ignored when "
        "the active container engine is Podman (Podman always uses the CLI).",
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
        """Builds and optionally pushes an image using the active engine.

        Args:
            image_name: Name of the image to build and push.
            build_context: The build context to use for the image.
            docker_build_options: Docker build options.
            container_registry: Optional container registry to push to.

        Returns:
            The Docker image repo digest or name.
        """
        engine = get_container_engine()
        if container_registry:
            self._check_registry_image(image_name, container_registry)

        engine.build(
            image_name=image_name,
            build_context=build_context,
            docker_build_options=docker_build_options,
            container_registry=container_registry,
            use_subprocess=self.config.use_subprocess_call,
        )

        if container_registry:
            return engine.push_image(image_name, container_registry)

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
