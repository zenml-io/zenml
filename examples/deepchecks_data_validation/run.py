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
from deepchecks import Dataset
from deepchecks.core import SuiteResult
from deepchecks.tabular.suites import full_suite
from rich import print
from sklearn import datasets

from zenml.integrations.constants import EVIDENTLY, SKLEARN
from zenml.integrations.deepchecks.steps import (
    DeepchecksDataValidatorConfig,
    DeepchecksDataValidatorStep,
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


data_validator = DeepchecksDataValidatorStep(
    DeepchecksDataValidatorConfig(
        column_mapping=None,
        profile_sections=["datadrift"],
    )
)


@step
def data_validator(
    train_df: pd.DataFrame, test_df: pd.DataFrame
) -> SuiteResult:
    """Validate data using deepchecks"""
    ds_train = Dataset(train_df)
    ds_test = Dataset(test_df)
    suite = full_suite()
    return suite.run(train_dataset=ds_train, test_dataset=ds_test)


@step
def post_validation(result: SuiteResult) -> bool:
    """Analyze the Deepchecks drift report and return a true/false value
    indicating whether data drift was detected."""
    print(result)
    return result.results[0]


@pipeline(required_integrations=[EVIDENTLY, SKLEARN])
def data_validation_pipeline(
    data_loader,
    data_splitter,
    data_validator,
    post_validation,
):
    """Links all the steps together in a pipeline"""
    data = data_loader()
    reference_dataset, comparison_dataset = data_splitter(data)
    validation_result = data_validator(
        reference_dataset=reference_dataset,
        comparison_dataset=comparison_dataset,
    )
    post_validation(validation_result)


def visualize_statistics():
    repo = Repository()
    pipe = repo.get_pipelines()[-1]
    evidently_outputs = pipe.runs[-1].get_step(name="data_validator")
    DeepchecksVisualizer().visualize(evidently_outputs)


if __name__ == "__main__":
    pipeline = data_validation_pipeline(
        data_loader=data_loader(),
        data_splitter=data_splitter(),
        data_validator=data_validator,
        post_validation=post_validation(),
    )
    pipeline.run()

    repo = Repository()
    pipeline = repo.get_pipeline(pipeline_name="data_validation_pipeline")
    last_run = pipeline.runs[-1]
    drift_analysis_step = last_run.get_step(name="data_validator")
    print(f"Data drift detected: {drift_analysis_step.output.read()}")

    drift_detection_step = last_run.get_step(name="data_validator")
    print(json.dumps(drift_detection_step.outputs["profile"].read(), indent=2))

    visualize_statistics()
