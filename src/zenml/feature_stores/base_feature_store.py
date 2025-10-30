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
"""The base class for feature stores."""

from abc import ABC, abstractmethod
from typing import Any, cast

from zenml.enums import StackComponentType
from zenml.stack import Flavor, StackComponent
from zenml.stack.stack_component import StackComponentConfig


class BaseFeatureStoreConfig(StackComponentConfig):
    """Base config for feature stores."""


class BaseFeatureStore(StackComponent, ABC):
    """Base class for all ZenML feature stores."""

    @property
    def config(self) -> BaseFeatureStoreConfig:
        """Returns the `BaseFeatureStoreConfig` config.

        Returns:
            The configuration.
        """
        return cast(BaseFeatureStoreConfig, self._config)

    @abstractmethod
    def get_historical_features(
        self,
        entity_df: Any,
        features: list[str],
        full_feature_names: bool = False,
    ) -> Any:
        """Returns the historical features for training or batch scoring.

        Args:
            entity_df: The entity DataFrame or entity name.
            features: The features to retrieve.
            full_feature_names: Whether to return the full feature names.

        Returns:
            The historical features.
        """

    @abstractmethod
    def get_online_features(
        self,
        entity_rows: list[dict[str, Any]],
        features: list[str],
        full_feature_names: bool = False,
    ) -> dict[str, Any]:
        """Returns the latest online feature data.

        Args:
            entity_rows: The entity rows to retrieve.
            features: The features to retrieve.
            full_feature_names: Whether to return the full feature names.

        Returns:
            The latest online feature data as a dictionary.
        """


class BaseFeatureStoreFlavor(Flavor):
    """Base class for all ZenML feature store flavors."""

    @property
    def type(self) -> StackComponentType:
        """Returns the flavor type.

        Returns:
            The flavor type.
        """
        return StackComponentType.FEATURE_STORE

    @property
    def config_class(self) -> type[BaseFeatureStoreConfig]:
        """Config class for this flavor.

        Returns:
            The config class.
        """
        return BaseFeatureStoreConfig

    @property
    @abstractmethod
    def implementation_class(self) -> type[BaseFeatureStore]:
        """Implementation class.

        Returns:
            The implementation class.
        """
        return BaseFeatureStore
