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
"""Kaniko image builder flavor."""

from typing import TYPE_CHECKING, List, Type

from zenml.config.base_settings import BaseSettings
from zenml.image_builders import BaseImageBuilderConfig, BaseImageBuilderFlavor
from zenml.integrations.kaniko import KANIKO_IMAGE_BUILDER_FLAVOR

if TYPE_CHECKING:
    from zenml.integrations.kaniko.image_builders import KanikoImageBuilder


KANIKO_EXECUTOR_IMAGE_TAG = "v1.9.1"
DEFAULT_KANIKO_EXECUTOR_IMAGE = (
    f"gcr.io/kaniko-project/executor:{KANIKO_EXECUTOR_IMAGE_TAG}"
)


class KanikoImageBuilderSettings(BaseSettings):
    """Settings for the Kaniko image builder."""


class KanikoImageBuilderConfig(
    BaseImageBuilderConfig, KanikoImageBuilderSettings
):
    """Kaniko image builder configuration.

    Attributes:
        kubernetes_context: The Kubernetes context in which to run the Kaniko
            pod.
        kubernetes_namespace: The Kubernetes namespace in which to run the
            Kaniko pod. This namespace will not be created and must already
            exist.
        executor_image: The image of the Kaniko executor to use.
    """

    kubernetes_context: str
    kubernetes_namespace: str = "zenml-kaniko"
    executor_image: str = DEFAULT_KANIKO_EXECUTOR_IMAGE

    executor_args: List[str] = []


class KanikoImageBuilderFlavor(BaseImageBuilderFlavor):
    """Kaniko image builder flavor."""

    @property
    def name(self) -> str:
        """The flavor name.

        Returns:
            The flavor name.
        """
        return KANIKO_IMAGE_BUILDER_FLAVOR

    @property
    def config_class(self) -> Type[KanikoImageBuilderConfig]:
        """Config class.

        Returns:
            The config class.
        """
        return KanikoImageBuilderConfig

    @property
    def implementation_class(self) -> Type["KanikoImageBuilder"]:
        """Implementation class.

        Returns:
            The implementation class.
        """
        from zenml.integrations.kaniko.image_builders import KanikoImageBuilder

        return KanikoImageBuilder
