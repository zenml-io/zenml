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
"""Implementation of the Feast Feature Store for ZenML."""

from typing import Any, Dict, List, Union, cast

import pandas as pd
from feast import FeatureStore  # type: ignore
from feast.infra.registry.base_registry import BaseRegistry  # type: ignore

from zenml.feature_stores.base_feature_store import BaseFeatureStore
from zenml.integrations.feast.flavors.feast_feature_store_flavor import (
    FeastFeatureStoreConfig,
)
from zenml.logger import get_logger

logger = get_logger(__name__)


class FeastFeatureStore(BaseFeatureStore):
    """Class to interact with the Feast feature store."""

    @property
    def config(self) -> FeastFeatureStoreConfig:
        """Returns the `FeastFeatureStoreConfig` config.

        Returns:
            The configuration.
        """
        return cast(FeastFeatureStoreConfig, self._config)

    def get_historical_features(
        self,
        entity_df: Union[pd.DataFrame, str],
        features: List[str],
        full_feature_names: bool = False,
    ) -> pd.DataFrame:
        """Returns the historical features for training or batch scoring.

        Args:
            entity_df: The entity DataFrame or entity name.
            features: The features to retrieve.
            full_feature_names: Whether to return the full feature names.

        Raise:
            ConnectionError: If the online component (Redis) is not available.

        Returns:
            The historical features as a Pandas DataFrame.
        """
        fs = FeatureStore(repo_path=self.config.feast_repo)

        return fs.get_historical_features(
            entity_df=entity_df,
            features=features,
            full_feature_names=full_feature_names,
        ).to_df()

    def get_online_features(
        self,
        entity_rows: List[Dict[str, Any]],
        features: List[str],
        full_feature_names: bool = False,
    ) -> Dict[str, Any]:
        """Returns the latest online feature data.

        Args:
            entity_rows: The entity rows to retrieve.
            features: The features to retrieve.
            full_feature_names: Whether to return the full feature names.

        Raise:
            ConnectionError: If the online component (Redis) is not available.

        Returns:
            The latest online feature data as a dictionary.
        """
        fs = FeatureStore(repo_path=self.config.feast_repo)

        return fs.get_online_features(  # type: ignore[no-any-return]
            entity_rows=entity_rows,
            features=features,
            full_feature_names=full_feature_names,
        ).to_dict()

    def get_data_sources(self) -> List[str]:
        """Returns the data sources' names.

        Raise:
            ConnectionError: If the online component (Redis) is not available.

        Returns:
            The data sources' names.
        """
        fs = FeatureStore(repo_path=self.config.feast_repo)
        return [ds.name for ds in fs.list_data_sources()]

    def get_entities(self) -> List[str]:
        """Returns the entity names.

        Raise:
            ConnectionError: If the online component (Redis) is not available.

        Returns:
            The entity names.
        """
        fs = FeatureStore(repo_path=self.config.feast_repo)
        return [ds.name for ds in fs.list_entities()]

    def get_feature_services(self) -> List[str]:
        """Returns the feature service names.

        Raise:
            ConnectionError: If the online component (Redis) is not available.

        Returns:
            The feature service names.
        """
        fs = FeatureStore(repo_path=self.config.feast_repo)
        return [ds.name for ds in fs.list_feature_services()]

    def get_feature_views(self) -> List[str]:
        """Returns the feature view names.

        Raise:
            ConnectionError: If the online component (Redis) is not available.

        Returns:
            The feature view names.
        """
        fs = FeatureStore(repo_path=self.config.feast_repo)
        return [ds.name for ds in fs.list_feature_views()]

    def get_project(self) -> str:
        """Returns the project name.

        Raise:
            ConnectionError: If the online component (Redis) is not available.

        Returns:
            The project name.
        """
        fs = FeatureStore(repo_path=self.config.feast_repo)
        return str(fs.project)

    def get_registry(self) -> BaseRegistry:
        """Returns the feature store registry.

        Raise:
            ConnectionError: If the online component (Redis) is not available.

        Returns:
            The registry.
        """
        fs: FeatureStore = FeatureStore(repo_path=self.config.feast_repo)
        return fs.registry

    def get_feast_version(self) -> str:
        """Returns the version of Feast used.

        Raise:
            ConnectionError: If the online component (Redis) is not available.

        Returns:
            The version of Feast currently being used.
        """
        fs = FeatureStore(repo_path=self.config.feast_repo)
        return str(fs.version())
