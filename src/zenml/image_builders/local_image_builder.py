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
from typing import Type, cast

from zenml.image_builders import (
    BaseImageBuilder,
    BaseImageBuilderConfig,
    BaseImageBuilderFlavor,
)


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
