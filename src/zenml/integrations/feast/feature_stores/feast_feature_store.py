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

from typing import Any, ClassVar

import redis  # type: ignore
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
    HOST: ClassVar[str] = "localhost"
    PORT: ClassVar[int] = 6379

    def __init__(self, *args: Any, **kwargs: Any):
        """Initializes the Feast feature store."""
        super().__init__(*args, **kwargs)
        self._validate_connection()

    def get_historical_features(self) -> DataFrame:
        """Returns the historical features for training or batch scoring."""
        return NotImplementedError

    def get_online_features(self) -> DataFrame:
        """Returns the latest online feature data."""
        return NotImplementedError

    def _validate_connection(self) -> None:
        """Validates the connection to the feature store."""
        client = redis.Redis(host=self.HOST, port=self.PORT)
        try:
            client.ping()
        except redis.exceptions.ConnectionError as e:
            raise RuntimeError(
                "Could not connect to feature store's online component. "
                "Please make sure that Redis is running."
            ) from e
