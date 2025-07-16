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
"""Feast feature store flavor."""

from typing import TYPE_CHECKING, Optional, Type

from pydantic import Field

from zenml.feature_stores.base_feature_store import (
    BaseFeatureStoreConfig,
    BaseFeatureStoreFlavor,
)
from zenml.integrations.feast import FEAST_FEATURE_STORE_FLAVOR

if TYPE_CHECKING:
    from zenml.integrations.feast.feature_stores import FeastFeatureStore


class FeastFeatureStoreConfig(BaseFeatureStoreConfig):
    """Config for Feast feature store.

    Configuration for connecting to Feast feature stores.
    Field descriptions are defined inline using Field() descriptors.
    """

    online_host: str = Field(
        default="localhost",
        description="Online feature store host address (typically Redis server).",
    )
    online_port: int = Field(
        default=6379, description="Online feature store port number."
    )
    feast_repo: str = Field(
        description="Local filesystem path to the Feast repository with feature definitions."
    )

    @property
    def is_local(self) -> bool:
        """Checks if this stack component is running locally.

        Returns:
            True if this config is for a local component, False otherwise.
        """
        return (
            self.online_host == "localhost" or self.online_host == "127.0.0.1"
        )


class FeastFeatureStoreFlavor(BaseFeatureStoreFlavor):
    """Feast Feature store flavor."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return FEAST_FEATURE_STORE_FLAVOR

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
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/feature_store/feast.png"

    @property
    def config_class(self) -> Type[FeastFeatureStoreConfig]:
        """Returns FeastFeatureStoreConfig config class.

        Returns:
                The config class.
        """
        """Config class for this flavor."""
        return FeastFeatureStoreConfig

    @property
    def implementation_class(self) -> Type["FeastFeatureStore"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.integrations.feast.feature_stores import FeastFeatureStore

        return FeastFeatureStore
