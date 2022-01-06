#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.

import pandas as pd
from sklearn import datasets

from zenml.integrations.evidently import steps as evidently_steps
from zenml.logger import get_logger
from zenml.pipelines import pipeline
from zenml.steps import step

logger = get_logger(__name__)


@step()
def data_loader() -> pd.DataFrame:
    """Load the breast cancer dataset."""
    breast_cancer = datasets.load_breast_cancer()
    df = pd.DataFrame(
        data=breast_cancer.data, columns=breast_cancer.feature_names
    )
    df["class"] = breast_cancer.target
    return df


@step
def full_split(
    input: pd.DataFrame,
) -> pd.DataFrame:
    """Loads the breast cancer dataset as a Pandas dataframe."""
    return [input]


@step
def partial_split(
    input: pd.DataFrame,
) -> pd.DataFrame:
    """Loads part of the breast cancer dataset as a Pandas dataframe."""
    return [input[:100]]


drift_detector = evidently_steps.EvidentlyDriftDetectionStep(
    evidently_steps.EvidentlyDriftDetectionConfig(column_mapping=None)
)

# @step()
# def drift_detector(full_data: pd.DataFrame, partial_data: pd.DataFrame) -> dict:
#     """Detects a drift in the pipeline."""
#     breast_cancer_data_drift_profile = Profile(
#         sections=[DataDriftProfileSection()]
#     )
#     breast_cancer_data_drift_profile.calculate(
#         full_data, partial_data, column_mapping=None
#     )
#     breast_cancer_data_drift_profile.json()
#     logger.info(breast_cancer_data_drift_profile.json())


@pipeline
def drift_detection_pipeline(
    data_loader,
    full_data,
    partial_data,
    drift_detector,
):
    """Links all the steps together in a pipeline"""
    data_loader = data_loader()
    full_data = full_data(data_loader)
    partial_data = partial_data(data_loader)
    drift_detector(full_data, partial_data)


pipeline = drift_detection_pipeline(
    data_loader=data_loader(),
    full_data=full_split(),
    partial_data=partial_split(),
    drift_detector=drift_detector(),
)

pipeline.run()
