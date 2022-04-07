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

import redis  # type: ignore
from feast import FeatureStore  # type: ignore[import]
from feast.feature_service import FeatureService  # type: ignore[import]
from pandas import DataFrame

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

    def get_historical_features(
        self,
        entity_df: Union[DataFrame, str],
        features: Union[List[str], FeatureService],
        full_feature_names: bool = False,
    ) -> DataFrame:
        """Returns the historical features for training or batch scoring."""
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
        features: Union[List[str], FeatureService],
        full_feature_names: bool = False,
    ) -> Dict[str, Any]:
        """Returns the latest online feature data."""
        self._validate_connection()
        fs = FeatureStore(repo_path=self.feast_repo)

        return fs.get_online_features(  # type: ignore[no-any-return]
            entity_rows=entity_rows,
            features=features,
            full_feature_names=full_feature_names,
        ).to_dict()

    def _validate_connection(self) -> None:
        """Validates the connection to the feature store."""
        client = redis.Redis(host=self.online_host, port=self.online_port)
        try:
            client.ping()
        except redis.exceptions.ConnectionError as e:
            raise RuntimeError(
                "Could not connect to feature store's online component. "
                "Please make sure that Redis is running."
            ) from e
