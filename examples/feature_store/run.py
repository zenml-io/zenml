#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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

import os
from datetime import datetime, timedelta

import pandas as pd
from pandas import DataFrame

from zenml.integrations.constants import FEAST
from zenml.integrations.feast.steps.feast_datasource import (
    FeastHistoricalDatasource,
    FeastHistoricalDatasourceConfig,
)
from zenml.logger import get_logger
from zenml.pipelines import pipeline
from zenml.repository import Repository
from zenml.steps import step

logger = get_logger(__name__)


@step
def print_initial_features(batch_features: DataFrame) -> DataFrame:
    """Prints features imported from the feature store."""
    return batch_features.head()


@pipeline(required_integrations=[FEAST])
def feast_pipeline(
    batch_features,
    feature_printer,
):
    """Links all the steps together in a pipeline"""
    features = batch_features()
    feature_printer(features)


batch_entity_df = pd.DataFrame.from_dict(
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
batch_config = FeastHistoricalDatasourceConfig(
    repo_path=os.path.join(os.getcwd(), "feast_feature_repo")
)

historical_data = FeastHistoricalDatasource(
    config=batch_config,
    entity_df=batch_entity_df,
    features=[
        "driver_hourly_stats:conv_rate",
        "driver_hourly_stats:acc_rate",
        "driver_hourly_stats:avg_daily_trips",
    ],
)

if __name__ == "__main__":
    pipeline = feast_pipeline(
        batch_features=historical_data,
        feature_printer=print_initial_features(),
    )

    pipeline.run()

    repo = Repository()
    pipeline = repo.get_pipeline("feast_pipeline")
    last_run = pipeline.runs[-1]
    features_step = last_run.get_step(name="feature_printer")
    print(features_step.output.read())
