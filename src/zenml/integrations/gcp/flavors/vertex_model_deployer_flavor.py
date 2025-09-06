#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Vertex AI model deployer flavor."""

from typing import TYPE_CHECKING, Optional, Type

from zenml.integrations.gcp import (
    GCP_RESOURCE_TYPE,
    VERTEX_MODEL_DEPLOYER_FLAVOR,
)
from zenml.integrations.gcp.flavors.vertex_base_config import (
    VertexAIBaseSettings,
)
from zenml.integrations.gcp.google_credentials_mixin import (
    GoogleCredentialsConfigMixin,
)
from zenml.model_deployers.base_model_deployer import (
    BaseModelDeployerConfig,
    BaseModelDeployerFlavor,
)
from zenml.models.v2.misc.service_connector_type import (
    ServiceConnectorRequirements,
)

if TYPE_CHECKING:
    from zenml.integrations.gcp.model_deployers.vertex_model_deployer import (
        VertexModelDeployer,
    )


class VertexModelDeployerConfig(
    BaseModelDeployerConfig,
    GoogleCredentialsConfigMixin,
    VertexAIBaseSettings,
):
    """Configuration for the Vertex AI model deployer.

    This configuration combines:
    - Base model deployer configuration
    - Google Cloud authentication
    - Vertex AI Base configuration
    """


class VertexModelDeployerFlavor(BaseModelDeployerFlavor):
    """Vertex AI model deployer flavor."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return VERTEX_MODEL_DEPLOYER_FLAVOR

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
    def config_class(self) -> Type[VertexModelDeployerConfig]:
        """Returns `VertexModelDeployerConfig` config class.

        Returns:
            The config class.
        """
        return VertexModelDeployerConfig

    @property
    def implementation_class(self) -> Type["VertexModelDeployer"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.integrations.gcp.model_deployers.vertex_model_deployer import (
            VertexModelDeployer,
        )

        return VertexModelDeployer
