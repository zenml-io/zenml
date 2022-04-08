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

from typing import Any, ClassVar, Dict, List, Union

import pandas as pd
import redis
from feast import FeatureStore  # type: ignore[import]

from zenml.feature_stores.base_feature_store import BaseFeatureStore
from zenml.logger import get_logger
from zenml.stack.stack_component_class_registry import (
    register_stack_component_class,
)

logger = get_logger(__name__)


@register_stack_component_class
class FeastFeatureStore(BaseFeatureStore):
    """Class to interact with the Feast feature store."""

    FLAVOR: ClassVar[str] = "feast"

    online_host: str = "localhost"
    online_port: int = 6379
    feast_repo: str

    def _validate_connection(self) -> None:
        """Validates the connection to the feature store.

        Raises:
            RuntimeError: If the online component (Redis) is not available.
        """
        client = redis.Redis(host=self.online_host, port=self.online_port)
        try:
            client.ping()
        except redis.exceptions.ConnectionError as e:
            raise redis.exceptions.ConnectionError(
                "Could not connect to feature store's online component. "
                "Please make sure that Redis is running."
            ) from e

    def get_historical_features(
        self,
        entity_df: Union[pd.DataFrame, str],
        features: List[str],
        full_feature_names: bool = False,
    ) -> pd.DataFrame:
        """Returns the historical features for training or batch scoring.

        Args:
            entity_df: The entity dataframe or entity name.
            features: The features to retrieve.
            full_feature_names: Whether to return the full feature names.

        Raise:
            ConnectionError: If the online component (Redis) is not available.

        Returns:
            The historical features as a Pandas DataFrame.
        """
        self._validate_connection()
        fs = FeatureStore(repo_path=self.feast_repo)

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
        self._validate_connection()
        fs = FeatureStore(repo_path=self.feast_repo)

        return fs.get_online_features(  # type: ignore[no-any-return]
            entity_rows=entity_rows,
            features=features,
            full_feature_names=full_feature_names,
        ).to_dict()
