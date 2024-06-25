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
"""GCP artifact store flavor."""

from typing import TYPE_CHECKING, ClassVar, Optional, Set, Type

from zenml.artifact_stores import (
    BaseArtifactStoreConfig,
    BaseArtifactStoreFlavor,
)
from zenml.integrations.gcp import GCP_ARTIFACT_STORE_FLAVOR, GCS_RESOURCE_TYPE
from zenml.models import ServiceConnectorRequirements
from zenml.stack.authentication_mixin import AuthenticationConfigMixin

if TYPE_CHECKING:
    from zenml.integrations.gcp.artifact_stores import GCPArtifactStore


GCP_PATH_PREFIX = "gs://"


class GCPArtifactStoreConfig(
    BaseArtifactStoreConfig, AuthenticationConfigMixin
):
    """Configuration for GCP Artifact Store."""

    SUPPORTED_SCHEMES: ClassVar[Set[str]] = {GCP_PATH_PREFIX}
    IS_IMMUTABLE_FILESYSTEM: ClassVar[bool] = True


class GCPArtifactStoreFlavor(BaseArtifactStoreFlavor):
    """Flavor of the GCP artifact store."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return GCP_ARTIFACT_STORE_FLAVOR

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
            resource_type=GCS_RESOURCE_TYPE,
            resource_id_attr="path",
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
    def config_class(self) -> Type[GCPArtifactStoreConfig]:
        """Returns GCPArtifactStoreConfig config class.

        Returns:
                The config class.
        """
        return GCPArtifactStoreConfig

    @property
    def implementation_class(self) -> Type["GCPArtifactStore"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.integrations.gcp.artifact_stores import GCPArtifactStore

        return GCPArtifactStore
