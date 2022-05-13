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


from datetime import datetime, timedelta
from typing import Any, Dict, List, Union

import pandas as pd

from zenml.exceptions import DoesNotExistException
from zenml.integrations.constants import FEAST
from zenml.logger import get_logger
from zenml.pipelines import pipeline
from zenml.repository import Repository
from zenml.steps import BaseStepConfig, StepContext, step

logger = get_logger(__name__)


historical_entity_dict = {
    "driver_id": [1001, 1002, 1003],
    "label_driver_reported_satisfaction": [1, 5, 3],
    "event_timestamp": [
        (datetime.now() - timedelta(minutes=11)).isoformat(),
        (datetime.now() - timedelta(minutes=36)).isoformat(),
        (datetime.now() - timedelta(minutes=73)).isoformat(),
    ],
}


features = [
    "driver_hourly_stats:conv_rate",
    "driver_hourly_stats:acc_rate",
    "driver_hourly_stats:avg_daily_trips",
]


class FeastHistoricalFeaturesConfig(BaseStepConfig):
    """Feast Feature Store historical data step configuration."""

    entity_dict: Union[Dict[str, Any], str]
    features: List[str]
    full_feature_names: bool = False

    class Config:
        arbitrary_types_allowed = True


@step
def get_historical_features(
    config: FeastHistoricalFeaturesConfig,
    context: StepContext,
) -> pd.DataFrame:
    """Feast Feature Store historical data step

    Args:
        config: The step configuration.
        context: The step context.

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
    config.entity_dict["event_timestamp"] = [
        datetime.fromisoformat(val)
        for val in config.entity_dict["event_timestamp"]
    ]
    entity_df = pd.DataFrame.from_dict(config.entity_dict)

    return feature_store_component.get_historical_features(
        entity_df=entity_df,
        features=config.features,
        full_feature_names=config.full_feature_names,
    )


historical_features = get_historical_features(
    config=FeastHistoricalFeaturesConfig(
        entity_dict=historical_entity_dict, features=features
    ),
)


@step
def print_historical_features(
    historical_features: pd.DataFrame,
) -> pd.DataFrame:
    """Prints features imported from the offline / batch feature store."""
    return historical_features.head()


@pipeline(required_integrations=[FEAST])
def feast_pipeline(
    get_features,
    feature_printer,
):
    """Links all the steps together in a pipeline"""
    features = get_features()
    feature_printer(features)


if __name__ == "__main__":
    pipeline = feast_pipeline(
        get_features=historical_features,
        feature_printer=print_historical_features(),
    )

    pipeline.run()

    repo = Repository()
    pipeline = repo.get_pipeline("feast_pipeline")
    last_run = pipeline.runs[-1]
    historical_features_step = last_run.get_step(name="feature_printer")
    print("HISTORICAL FEATURES:")
    print(historical_features_step.output.read())
