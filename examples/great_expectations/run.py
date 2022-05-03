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
from sklearn.datasets import fetch_openml

from zenml.console import console
from zenml.integrations.constants import GREAT_EXPECTATIONS, SKLEARN
from zenml.integrations.great_expectations.steps.great_expectations_checkpoint import (
    GreatExpectationsCheckpointConfig,
    GreatExpectationsCheckpointStep,
)
from zenml.integrations.great_expectations.visualizers.great_expectations_visualizer import (
    GreatExpectationsVisualizer,
)
from zenml.pipelines import pipeline
from zenml.repository import Repository
from zenml.steps import Output, step

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
    plates = fetch_openml(name="steel-plates-fault")
    df = pd.DataFrame(data=plates.data, columns=plates.feature_names)
    df["target"] = plates.target
    plates_columns = dict(zip(plates.feature_names, FULL_FEATURE_NAMES))
    df.rename(columns=plates_columns, inplace=True)
    return df


@step
def splitter(
    df: pd.DataFrame,
) -> Output(train=pd.DataFrame, test=pd.DataFrame):
    train, test = df.iloc[: int(len(df) * 0.8)], df.iloc[int(len(df) * 0.8) :]
    return train, test


ge_config = GreatExpectationsCheckpointConfig(
    context_path="./great_expectations/",
    datasource_name="zenml_datasource",
    expectation_suite_name="ge_suite",
    data_asset_name="plates_train_df",
)
ge_step = GreatExpectationsCheckpointStep(config=ge_config)


@pipeline(required_integrations=[SKLEARN, GREAT_EXPECTATIONS])
def validation_pipeline(importer, splitter, validator):
    imported_data = importer()
    _, test = splitter(imported_data)
    validator(test)


if __name__ == "__main__":
    pipeline = validation_pipeline(importer(), splitter(), ge_step)
    pipeline.run()

    repo = Repository()
    pipeline = repo.get_pipeline("validation_pipeline")
    last_run = pipeline.runs[-1]
    validation_step = last_run.get_step(name="validator")
    results = validation_step.outputs["results"].read()
    datadoc_path = validation_step.outputs["data_doc"].read()
    if not results["success"]:
        console.print("Data failed to pass the Expectations Suite. \n")
        console.print(results)
        GreatExpectationsVisualizer().visualize(datadoc_path)
