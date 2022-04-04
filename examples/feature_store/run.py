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
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import redis
import redis_server
from feast import FeatureStore
from feast.repo_config import load_repo_config
from pandas import DataFrame

from zenml.integrations.constants import FEAST
from zenml.logger import get_logger

# from zenml.integrations.feast.steps import feast_ingestion, feast_retrieval
from zenml.pipelines import pipeline
from zenml.repository import Repository
from zenml.steps import step

logger = get_logger(__name__)


# def pretty_print_dataframe(df: DataFrame) -> DataFrame:
#     """Pretty prints a dataframe."""
#     logger.info(df)


# feature_importer = feast_ingestion.FeatureImporter(source="xx")
# batch_features = feast_retrieval.BatchFeatureRetrieval(entities="xx")
# online_features = feast_retrieval.OnlineFeatureRetrieval(entities="yy")


# @pipeline(required_integrations=[FEAST])
# def feast_pipeline(
#     feature_import,
#     batch_features,
#     online_features,
#     feature_printer,
# ):
#     """Links all the steps together in a pipeline"""
#     feature_import()
#     batch_features = batch_features()
#     print("These features are batch/offline features:")
#     feature_printer(batch_features)

#     print("These features are online features:")
#     feature_printer(online_features)


@step
def get_batch_data() -> DataFrame:
    """Retrieves batch data from the feature store."""
    # The entity dataframe is the dataframe we want to enrich with feature values
    entity_df = pd.DataFrame.from_dict(
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

    store = FeatureStore(
        repo_path=os.path.join(
            os.getcwd(), "examples", "feature_store", "feast_feature_repo"
        )
    )

    return store.get_historical_features(
        entity_df=entity_df,
        features=[
            "driver_hourly_stats:conv_rate",
            "driver_hourly_stats:acc_rate",
            "driver_hourly_stats:avg_daily_trips",
        ],
    ).to_df()


@step
def print_initial_features(batch_features: DataFrame) -> None:
    """Prints features imported from the feature store."""
    return batch_features.head()


@pipeline(required_integrations=[FEAST])
def feast_pipeline(
    batch_features,
    feature_printer,
):
    """Links all the steps together in a pipeline"""
    batch_features = batch_features()
    print("These features are batch/offline features:")
    feature_printer(batch_features)


if __name__ == "__main__":
    subprocess.run([f"{redis_server.REDIS_SERVER_PATH}", "--daemonize", "yes"])

    host = "localhost"
    port = 6379

    client = redis.Redis(host=host, port=port)
    repo = Path(
        os.path.join(
            os.getcwd(), "examples", "feature_store", "feast_feature_repo"
        )
    )
    repo_config = load_repo_config(repo)

    # RUN THE `feast apply` command from within `feast_feature_repo`
    # subprocess.run("cd", "examples/feature_store/feast_feature_repo")
    # subprocess.run("feast", "apply")

    pipeline = feast_pipeline(
        batch_features=get_batch_data(),
        feature_printer=print_initial_features(),
    )

    repo = Repository()
    pipeline = repo.get_pipeline("feast_pipeline")
    last_run = pipeline.runs[-1]
    features_step = last_run.get_step(name="print_initial_features")
    print(features_step.output.read())

    # pipeline = feast_pipeline(
    #     feature_importer=feature_importer(),
    #     batch_features=batch_features(),
    #     online_features=online_features(),
    #     feature_printer=print_initial_features(),
    # )

    # pipeline.run()
