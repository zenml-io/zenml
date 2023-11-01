#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""Huggingface model registry flavor."""

from typing import TYPE_CHECKING, Optional, Type

from zenml.integrations.huggingface import HUGGINGFACE_MODEL_REGISTRY_FLAVOR
from zenml.model_registries.base_model_registry import (
    BaseModelRegistryConfig,
    BaseModelRegistryFlavor,
)
from zenml.utils.secret_utils import SecretField

if TYPE_CHECKING:
    from zenml.integrations.huggingface.model_registries import (
        HuggingfaceModelRegistry,
    )


class HuggingfaceModelRegistryConfig(BaseModelRegistryConfig):
    """Configuration for the Huggingface model registry."""

    user: str = SecretField()
    token: str = SecretField()


class HuggingfaceModelRegistryFlavor(BaseModelRegistryFlavor):
    """Model registry flavor for Huggingface models."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return HUGGINGFACE_MODEL_REGISTRY_FLAVOR

    @property
    def docs_url(self) -> Optional[str]:
        """A url to point at docs explaining this flavor.

        Returns:
            A flavor docs url.
        """
        return self.generate_default_docs_url()

    @property
    def sdk_docs_url(self) -> Optional[str]:
        """A url to point at SDK docs explaining this flavor.

        Returns:
            A flavor SDK docs url.
        """
        return self.generate_default_sdk_docs_url()

    @property
    def logo_url(self) -> str:
        """A url to represent the flavor in the dashboard.

        Returns:
            The flavor logo.
        """
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/model_registry/huggingface.png"

    @property
    def config_class(self) -> Type[HuggingfaceModelRegistryConfig]:
        """Returns `HuggingfaceModelRegistryConfig` config class.

        Returns:
                The config class.
        """
        return HuggingfaceModelRegistryConfig

    @property
    def implementation_class(self) -> Type["HuggingfaceModelRegistry"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.integrations.huggingface.model_registries import (
            HuggingfaceModelRegistry,
        )

        return HuggingfaceModelRegistry
