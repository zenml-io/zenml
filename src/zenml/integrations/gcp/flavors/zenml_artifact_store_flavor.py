#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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

from typing import Type

from zenml.integrations.gcp import ZENML_ARTIFACT_STORE_FLAVOR
from zenml.integrations.gcp.artifact_stores.zenml_artifact_store import (
    ZenMLArtifactStore,
)
from zenml.integrations.gcp.flavors.gcp_artifact_store_flavor import (
    GCPArtifactStoreConfig,
    GCPArtifactStoreFlavor,
)


class ZenMLArtifactStoreConfig(GCPArtifactStoreConfig):
    """Configuration for ZenML specialized Artifact Store."""

    pass


class ZenMLArtifactStoreFlavor(GCPArtifactStoreFlavor):
    """Flavor of the ZenML specialized artifact store."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return ZENML_ARTIFACT_STORE_FLAVOR

    @property
    def logo_url(self) -> str:
        """A url to represent the flavor in the dashboard.

        Returns:
            The flavor logo.
        """
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/artifact_store/zenml.png"

    @property
    def config_class(self) -> Type[ZenMLArtifactStoreConfig]:
        """Returns ZenMLArtifactStoreConfig config class.

        Returns:
                The config class.
        """
        return ZenMLArtifactStoreConfig

    @property
    def implementation_class(self) -> Type["ZenMLArtifactStore"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.integrations.gcp.artifact_stores.zenml_artifact_store import (
            ZenMLArtifactStore,
        )

        return ZenMLArtifactStore
