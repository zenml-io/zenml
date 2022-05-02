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

import json

import pandas as pd
from deepchecks.core import SuiteResult
from rich import print
from sklearn import datasets

from zenml.integrations.constants import EVIDENTLY, SKLEARN
from zenml.integrations.deepchecks.steps import (
    DeepchecksProfileConfig,
    DeepchecksProfileStep,
)
from zenml.integrations.deepchecks.visualizers import DeepchecksVisualizer
from zenml.logger import get_logger
from zenml.pipelines import pipeline
from zenml.repository import Repository
from zenml.steps import Output, step

logger = get_logger(__name__)


@step
def data_loader() -> pd.DataFrame:
    """Load the breast cancer dataset."""
    breast_cancer = datasets.load_breast_cancer()
    df = pd.DataFrame(
        data=breast_cancer.data, columns=breast_cancer.feature_names
    )
    df["class"] = breast_cancer.target
    return df


@step
def data_splitter(
    input_df: pd.DataFrame,
) -> Output(reference_dataset=pd.DataFrame, comparison_dataset=pd.DataFrame):
    """Splits the dataset into two subsets, the reference dataset and the
    comparison dataset"""
    return input_df[100:], input_df[:100]


drift_detector = DeepchecksProfileStep(
    DeepchecksProfileConfig(
        column_mapping=None,
        profile_sections=["datadrift"],
    )
)


@step
def validate_data(result: SuiteResult) -> bool:
    """Analyze the Deepchecks drift report and return a true/false value
    indicating whether data drift was detected."""
    return result.results[0]


@pipeline(required_integrations=[EVIDENTLY, SKLEARN])
def drift_detection_pipeline(
    data_loader,
    data_splitter,
    drift_detector,
    data_validator,
):
    """Links all the steps together in a pipeline"""
    data = data_loader()
    reference_dataset, comparison_dataset = data_splitter(data)
    drift_report, _ = drift_detector(
        reference_dataset=reference_dataset,
        comparison_dataset=comparison_dataset,
    )
    data_validator(drift_report)


def visualize_statistics():
    repo = Repository()
    pipe = repo.get_pipelines()[-1]
    evidently_outputs = pipe.runs[-1].get_step(name="drift_detector")
    DeepchecksVisualizer().visualize(evidently_outputs)


if __name__ == "__main__":
    pipeline = drift_detection_pipeline(
        data_loader=data_loader(),
        data_splitter=data_splitter(),
        drift_detector=drift_detector,
        data_validator=validate_data(),
    )
    pipeline.run()

    repo = Repository()
    pipeline = repo.get_pipeline(pipeline_name="drift_detection_pipeline")
    last_run = pipeline.runs[-1]
    drift_analysis_step = last_run.get_step(name="data_validator")
    print(f"Data drift detected: {drift_analysis_step.output.read()}")

    drift_detection_step = last_run.get_step(name="drift_detector")
    print(json.dumps(drift_detection_step.outputs["profile"].read(), indent=2))

    visualize_statistics()
