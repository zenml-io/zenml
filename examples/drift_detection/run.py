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

from evidently.dashboard import Dashboard
from evidently.tabs import DataDriftTab

from zenml.pipelines import pipeline
from zenml.steps import Output, step
from zenml.logger import get_logger

logger = get_logger(__name__)


@step
def data_loader() -> Output(dataset=pd.DataFrame):
    """Load the breast cancer dataset."""
    return datasets.load_breast_cancer()


@step
def full_split(input: pd.DataFrame) -> Output(
    dataset=pd.DataFrame,
):
    """Loads the breast cancer dataset as a Pandas dataframe."""
    return pd.DataFrame(input.data, columns=input.feature_names)


@step
def partial_split(input: pd.DataFrame) -> Output(
    dataset=pd.DataFrame,
):
    """Loads part of the breast cancer dataset as a Pandas dataframe."""
    return pd.DataFrame(input.data, columns=input.feature_names)[:100]


@step()
def drift_detector(full_data: pd.DataFrame, partial_data: pd.DataFrame) -> None:
    """Detects a drift in the pipeline."""
    breast_cancer_data_drift_report = Dashboard(tabs=[DataDriftTab()])
    breast_cancer_data_drift_report.calculate(full_data, partial_data, column_mapping=None)
    breast_cancer_data_drift_report.save("reports/breast_cancer_drift_report.html")
    # logger.info("Drift detected")


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
