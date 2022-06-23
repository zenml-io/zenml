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


import pandas as pd
from great_expectations.core import ExpectationSuite  # type: ignore[import]
from sklearn.datasets import fetch_openml

from zenml.integrations.constants import GREAT_EXPECTATIONS, SKLEARN
from zenml.integrations.great_expectations.steps import (
    GreatExpectationsProfilerConfig,
    GreatExpectationsProfilerStep,
    GreatExpectationsValidatorConfig,
    GreatExpectationsValidatorStep,
)
from zenml.integrations.great_expectations.visualizers.ge_visualizer import (
    GreatExpectationsVisualizer,
)
from zenml.pipelines import pipeline
from zenml.repository import Repository
from zenml.steps import Output, step
from zenml.steps.utils import clone_step

FULL_FEATURE_NAMES = [
    name.lower()
    for name in [
        "X_Minimum",
        "X_Maximum",
        "Y_Minimum",
        "Y_Maximum",
        "Pixels_Areas",
        "X_Perimeter",
        "Y_Perimeter",
        "Sum_of_Luminosity",
        "Minimum_of_Luminosity",
        "Maximum_of_Luminosity",
        "Length_of_Conveyer",
        "TypeOfSteel_A300",
        "TypeOfSteel_A400",
        "Steel_Plate_Thickness",
        "Edges_Index",
        "Empty_Index",
        "Square_Index",
        "Outside_X_Index",
        "Edges_X_Index",
        "Edges_Y_Index",
        "Outside_Global_Index",
        "LogOfAreas",
        "Log_X_Index",
        "Log_Y_Index",
        "Orientation_Index",
        "Luminosity_Index",
        "SigmoidOfAreas",
        "Pastry",
        "Z_Scratch",
        "K_Scatch",
        "Stains",
        "Dirtiness",
        "Bumps",
        "Other_Faults",
    ]
]


@step
def importer() -> pd.DataFrame:
    """Import the OpenML Steel Plates Fault Dataset.

    The Steel Plates Faults Data Set is provided by Semeion, Research Center of
    Sciences of Communication, Via Sersale 117, 00128, Rome, Italy
    (https://www.openml.org/search?type=data&sort=runs&id=1504&status=active).

    Returns:
        pd.DataFrame: the steel plates fault dataset.
    """
    plates = fetch_openml(name="steel-plates-fault")
    df = pd.DataFrame(data=plates.data, columns=plates.feature_names)
    df["target"] = plates.target
    plates_columns = dict(zip(plates.feature_names, FULL_FEATURE_NAMES))
    df.rename(columns=plates_columns, inplace=True)
    return df


ge_profiler_config = GreatExpectationsProfilerConfig(
    expectation_suite_name="steel_plates_suite",
    data_asset_name="steel_plates_train_df",
)
ge_profiler_step = GreatExpectationsProfilerStep(config=ge_profiler_config)


@step
def splitter(
    df: pd.DataFrame,
) -> Output(train=pd.DataFrame, test=pd.DataFrame):
    train, test = df.iloc[: int(len(df) * 0.8)], df.iloc[int(len(df) * 0.8) :]
    return train, test


ge_validate_train_config = GreatExpectationsValidatorConfig(
    expectation_suite_name="steel_plates_suite",
    data_asset_name="steel_plates_train_df",
)
# We clone the builtin step by calling the `clone_step` utility to use it twice
# in our pipeline: on the training set and on the validation set.
# This is necessary because a step cannot be used twice in the same pipeline.
ge_validate_train_step = clone_step(
    GreatExpectationsValidatorStep, "ge_validate_train_step_class"
)(config=ge_validate_train_config)

ge_validate_test_config = GreatExpectationsValidatorConfig(
    expectation_suite_name="steel_plates_suite",
    data_asset_name="steel_plates_test_df",
)
ge_validate_test_step = clone_step(
    GreatExpectationsValidatorStep, "ge_validate_test_step_class"
)(config=ge_validate_test_config)


@step
def prevalidator(
    suite: ExpectationSuite,
) -> bool:
    """
    This step is necessary to make sure that the validation step is only run
    after the profiler step has finished.
    """
    return True


@pipeline(
    enable_cache=False, required_integrations=[SKLEARN, GREAT_EXPECTATIONS]
)
def validation_pipeline(
    importer, splitter, profiler, prevalidator, train_validator, test_validator
):
    imported_data = importer()
    train, test = splitter(imported_data)
    suite = profiler(train)
    condition = prevalidator(suite)
    train_validator(train, condition)
    test_validator(test, condition)


def visualize_results(pipeline_name: str, step_name: str) -> None:
    repo = Repository()
    pipeline = repo.get_pipeline(pipeline_name)
    last_run = pipeline.runs[-1]
    validation_step = last_run.get_step(name=step_name)
    GreatExpectationsVisualizer().visualize(validation_step)


if __name__ == "__main__":
    pipeline = validation_pipeline(
        importer(),
        splitter(),
        ge_profiler_step,
        prevalidator(),
        ge_validate_train_step,
        ge_validate_test_step,
    )
    pipeline.run()

    visualize_results("validation_pipeline", "profiler")
    visualize_results("validation_pipeline", "train_validator")
    visualize_results("validation_pipeline", "test_validator")
