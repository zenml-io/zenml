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
"""Azure artifact store flavor."""

from typing import TYPE_CHECKING, ClassVar, Set, Type

from zenml.artifact_stores import (
    BaseArtifactStoreConfig,
    BaseArtifactStoreFlavor,
)
from zenml.integrations.azure import AZURE_ARTIFACT_STORE_FLAVOR
from zenml.stack.authentication_mixin import AuthenticationConfigMixin

if TYPE_CHECKING:
    from zenml.integrations.azure.artifact_stores import AzureArtifactStore


class AzureArtifactStoreConfig(
    BaseArtifactStoreConfig, AuthenticationConfigMixin
):
    """Configuration class for Azure Artifact Store."""

    SUPPORTED_SCHEMES: ClassVar[Set[str]] = {"abfs://", "az://"}


class AzureArtifactStoreFlavor(BaseArtifactStoreFlavor):
    """Azure Artifact Store flavor."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return AZURE_ARTIFACT_STORE_FLAVOR

    @property
    def config_class(self) -> Type[AzureArtifactStoreConfig]:
        """Returns AzureArtifactStoreConfig config class.

        Returns:
            The config class.
        """
        return AzureArtifactStoreConfig

    @property
    def implementation_class(self) -> Type["AzureArtifactStore"]:
        """Implementation class.

        Returns:
            The implementation class.
        """
        from zenml.integrations.azure.artifact_stores import AzureArtifactStore

        return AzureArtifactStore
