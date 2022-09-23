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

from typing import TYPE_CHECKING, ClassVar, Set, Type

from zenml.artifact_stores import (
    BaseArtifactStoreConfig,
    BaseArtifactStoreFlavor,
)
from zenml.integrations.gcp import GCP_ARTIFACT_STORE_FLAVOR
from zenml.stack.authentication_mixin import AuthenticationConfigMixin

if TYPE_CHECKING:
    from zenml.integrations.gcp.artifact_stores import GCPArtifactStore


GCP_PATH_PREFIX = "gs://"


class GCPArtifactStoreConfig(
    BaseArtifactStoreConfig, AuthenticationConfigMixin
):
    """Configuration for GCP Artifact Store."""

    SUPPORTED_SCHEMES: ClassVar[Set[str]] = {GCP_PATH_PREFIX}


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
