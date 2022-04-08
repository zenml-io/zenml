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

import pandas as pd
from pandas import DataFrame

from zenml.integrations.constants import FEAST
from zenml.integrations.feast.steps.feast_feature_store_step import (
    feast_historical_features_step,
    feast_online_features_step,
)
from zenml.logger import get_logger
from zenml.pipelines import pipeline
from zenml.repository import Repository
from zenml.steps import step

logger = get_logger(__name__)


historical_entity_df = pd.DataFrame.from_dict(
    {
        "driver_id": [1001, 1002, 1003],
        "label_driver_reported_satisfaction": [1, 5, 3],
        "event_timestamp": [
            datetime.now() - timedelta(minutes=11),
            datetime.now() - timedelta(minutes=36),
            datetime.now() - timedelta(minutes=73),
        ],
    }
)

features = [
    "driver_hourly_stats:conv_rate",
    "driver_hourly_stats:acc_rate",
    "driver_hourly_stats:avg_daily_trips",
]

historical_feature_data_importer = feast_historical_features_step(
    name="historical_features",
    entity_df=historical_entity_df,
    features=features,
)
online_feature_data_importer = feast_online_features_step(
    name="online_features",
    features=features,
    entity_rows=[
        {"driver_id": 1004},
        {"driver_id": 1005},
    ],
)

historical_features = historical_feature_data_importer()
online_features = online_feature_data_importer()


@step
def print_historical_features(historical_features: DataFrame) -> DataFrame:
    """Prints features imported from the offline / batch feature store."""
    return historical_features.head()


@step
def print_online_features(features_dict: dict) -> dict:
    """Prints features imported from the online feature store."""
    return features_dict


@pipeline(required_integrations=[FEAST])
def feast_pipeline(
    historical_features,
    online_features,
    historical_feature_printer,
    online_feature_printer,
):
    """Links all the steps together in a pipeline"""
    historical_features = historical_features()
    historical_feature_printer(historical_features)
    online_features = online_features()
    online_feature_printer(online_features)


if __name__ == "__main__":
    pipeline = feast_pipeline(
        historical_features=historical_features,
        online_features=online_features,
        historical_feature_printer=print_historical_features(),
        online_feature_printer=print_online_features(),
    )

    pipeline.run()

    repo = Repository()
    pipeline = repo.get_pipeline("feast_pipeline")
    last_run = pipeline.runs[-1]
    historical_features_step = last_run.get_step(
        name="historical_feature_printer"
    )
    online_features_step = last_run.get_step(name="online_feature_printer")
    print("HISTORICAL FEATURES:")
    print(historical_features_step.output.read())
    print("\nONLINE FEATURES:")
    print(online_features_step.output.read())
