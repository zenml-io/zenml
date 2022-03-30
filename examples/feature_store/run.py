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

from pandas import DataFrame

from zenml.integrations.constants import FEAST
from zenml.integrations.feast.steps import feast_ingestion, feast_retrieval
from zenml.pipelines import pipeline
from zenml.steps import step


def pretty_print_dataframe(df: DataFrame) -> None:
    """Pretty prints a dataframe."""
    print(df)


feature_importer = feast_ingestion.FeatureImporter(source="xx")
batch_features = feast_retrieval.BatchFeatureRetrieval(entities="xx")


@step
def print_initial_features(batch_features: DataFrame) -> None:
    """Prints features imported from the feature store."""
    pretty_print_dataframe(batch_features.head())


@pipeline(required_integrations=[FEAST])
def feast_pipeline(
    feature_import,
    batch_features,
    feature_printer,
):
    """Links all the steps together in a pipeline"""
    feature_import()
    batch_features = batch_features()
    feature_printer(batch_features)


if __name__ == "__main__":
    pipeline = feast_pipeline(
        feature_importer=feature_importer(),
        batch_features=batch_features(),
        feature_printer=print_initial_features(),
    )

    pipeline.run()
