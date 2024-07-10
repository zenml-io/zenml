from datetime import datetime
from typing import Any, Dict, List, Union

import pandas as pd

from zenml.exceptions import DoesNotExistException
from zenml.logger import get_logger
from zenml.steps import BaseParameters, StepContext
from zenml import step
from zenml.client import Client

logger = get_logger(__name__)


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

@step(enable_cache=False)
def get_historical_features() -> pd.DataFrame:
    """Feast Feature Store historical data step.

    Args:
        params: The step parameters.

    Returns:
        The historical features as a DataFrame.
    """
    active_stack = Client().active_stack
    feature_store_component = active_stack.feature_store
    historical_entity_dict["event_timestamp"] = [
        datetime.fromisoformat(val) for val in historical_entity_dict["event_timestamp"]
    ]
    entity_df = pd.DataFrame.from_dict(historical_entity_dict)

    return feature_store_component.get_historical_features(
        entity_df=entity_df,
        features=features,
        full_feature_names=False,
    )
