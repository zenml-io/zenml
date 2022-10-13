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

from typing import TYPE_CHECKING, Type

from zenml.feature_stores.base_feature_store import (
    BaseFeatureStoreConfig,
    BaseFeatureStoreFlavor,
)
from zenml.integrations.feast import FEAST_FEATURE_STORE_FLAVOR

if TYPE_CHECKING:
    from zenml.integrations.feast.feature_stores import FeastFeatureStore


class FeastFeatureStoreConfig(BaseFeatureStoreConfig):
    """Config for Feast feature store."""

    online_host: str = "localhost"
    online_port: int = 6379
    feast_repo: str

    @property
    def is_local(self) -> bool:
        """Checks if this stack component is running locally.

        This designation is used to determine if the stack component can be
        shared with other users or if it is only usable on the local host.

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
