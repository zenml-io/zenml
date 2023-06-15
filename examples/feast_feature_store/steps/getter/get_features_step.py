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


from datetime import datetime
from typing import Any, Dict, List

import pandas as pd

from zenml import step
from zenml.exceptions import DoesNotExistException
from zenml.logger import get_logger
from zenml.steps import StepContext

logger = get_logger(__name__)


@step(enable_cache=False)
def get_historical_features(
    context: StepContext,
    entity_dict: Dict[str, Any],
    features: List[str],
    full_feature_names: bool = False,
) -> pd.DataFrame:
    """Feast Feature Store historical data step.

    Args:
        context: The step context.
        entity_dict: The entity dictionary.
        features: The list of features to retrieve.
        full_feature_names: Whether to use full feature names.

    Returns:
        The historical features as a DataFrame.
    """
    if not context.stack:
        raise DoesNotExistException(
            "No active stack is available. Please make sure that you have registered and set a stack."
        )
    elif not context.stack.feature_store:
        raise DoesNotExistException(
            "The Feast feature store component is not available. "
            "Please make sure that the Feast stack component is registered as part of your current active stack."
        )

    feature_store_component = context.stack.feature_store
    entity_dict["event_timestamp"] = [
        datetime.fromisoformat(val) for val in entity_dict["event_timestamp"]
    ]
    entity_df = pd.DataFrame.from_dict(entity_dict)

    return feature_store_component.get_historical_features(
        entity_df=entity_df,
        features=features,
        full_feature_names=full_feature_names,
    )


historical_entity_dict = {
    "driver_id": [1001, 1002, 1003],
    "label_driver_reported_satisfaction": [1, 5, 3],
    "event_timestamp": [
        datetime(2021, 4, 12, 10, 59, 42).isoformat(),
        datetime(2021, 4, 12, 8, 12, 10).isoformat(),
        datetime(2021, 4, 12, 16, 40, 26).isoformat(),
    ],
    "val_to_add": [1, 2, 3],
    "val_to_add_2": [10, 20, 30],
}


features = [
    "driver_hourly_stats:conv_rate",
    "driver_hourly_stats:acc_rate",
    "driver_hourly_stats:avg_daily_trips",
    "transformed_conv_rate:conv_rate_plus_val1",
    "transformed_conv_rate:conv_rate_plus_val2",
]


get_features = get_historical_features.with_options(
    parameters=dict(entity_dict=historical_entity_dict, features=features),
)
