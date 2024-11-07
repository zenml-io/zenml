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
"""VertexAI model registry flavor."""

from typing import TYPE_CHECKING, Optional, Type

from zenml.config.base_settings import BaseSettings
from zenml.integrations.gcp import (
    GCP_RESOURCE_TYPE,
    VERTEX_MODEL_REGISTRY_FLAVOR,
)
from zenml.integrations.gcp.google_credentials_mixin import (
    GoogleCredentialsConfigMixin,
)
from zenml.model_registries.base_model_registry import (
    BaseModelRegistryConfig,
    BaseModelRegistryFlavor,
)
from zenml.models import ServiceConnectorRequirements

if TYPE_CHECKING:
    from zenml.integrations.gcp.model_registries import (
        VertexAIModelRegistry,
    )


class VertexAIModelRegistrySettings(BaseSettings):
    """Settings for the VertexAI model registry."""

    location: str


class VertexAIModelRegistryConfig(
    BaseModelRegistryConfig,
    GoogleCredentialsConfigMixin,
    VertexAIModelRegistrySettings,
):
    """Configuration for the VertexAI model registry."""


class VertexModelRegistryFlavor(BaseModelRegistryFlavor):
    """Model registry flavor for VertexAI models."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return VERTEX_MODEL_REGISTRY_FLAVOR

    @property
    def service_connector_requirements(
        self,
    ) -> Optional[ServiceConnectorRequirements]:
        """Service connector resource requirements for service connectors.

        Specifies resource requirements that are used to filter the available
        service connector types that are compatible with this flavor.

        Returns:
            Requirements for compatible service connectors, if a service
            connector is required for this flavor.
        """
        return ServiceConnectorRequirements(
            resource_type=GCP_RESOURCE_TYPE,
        )

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
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/artifact_store/gcp.png"

    @property
    def config_class(self) -> Type[VertexAIModelRegistryConfig]:
        """Returns `VertexAIModelRegistryConfig` config class.

        Returns:
                The config class.
        """
        return VertexAIModelRegistryConfig

    @property
    def implementation_class(self) -> Type["VertexAIModelRegistry"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.integrations.gcp.model_registries import (
            VertexAIModelRegistry,
        )

        return VertexAIModelRegistry
