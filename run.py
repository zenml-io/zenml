#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
#
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

import os
from typing import Type

os.environ["ZENML_DEBUG"] = "true"
import pandas as pd

from zenml import pipeline
from zenml.materializers.pandas_materializer import PandasMaterializer
from zenml.steps import step
from zenml.steps.base_step_config import BaseStepConfig
from zenml.steps.step_output import Output


class StepConfig(BaseStepConfig):
    basic_param_1: int = 1
    basic_param_2: str = 2


class PandasJSONMaterializer(PandasMaterializer):
    DATA_FILENAME = "data.json"

    def handle_input(self, data_type: Type) -> pd.DataFrame:
        """Reads all files inside the artifact directory and concatenates
        them to a pandas dataframe."""
        return pd.read_json(os.path.join(self.artifact.uri, self.DATA_FILENAME))

    def handle_return(self, df: pd.DataFrame):
        """Writes a pandas dataframe to the specified filename.

        Args:
            df: The pandas dataframe to write.
        """
        filepath = os.path.join(self.artifact.uri, self.DATA_FILENAME)
        df.to_json(filepath)


@step
def number_returner(
    config: StepConfig,
) -> Output(number=int, non_number=int):
    return config.basic_param_1 + int(config.basic_param_2), "test"


@step
def import_dataframe_csv(sum: int) -> pd.DataFrame:
    print(sum)
    return pd.DataFrame({"sum": [sum]})


@step
def import_dataframe_json(sum: int) -> pd.DataFrame:
    return pd.DataFrame({"sum": [sum]})


@step
def last_step_1(df: pd.DataFrame) -> pd.DataFrame:
    return df


@step
def last_step_2(df: pd.DataFrame) -> pd.DataFrame:
    return df


@pipeline
def my_pipeline(
    step_1,
    step_2_1,
    step_2_2,
    step_3_1,
    step_3_2,
):
    number, non_number = step_1()
    df_csv = step_2_1(sum=number)
    df_json = step_2_2(sum=number)
    step_3_1(df=df_csv)
    step_3_2(df=df_json)


# Pipeline
split_pipeline = my_pipeline(
    step_1=number_returner(config=StepConfig(basic_param_2="2")),
    step_2_1=import_dataframe_csv(),
    step_2_2=import_dataframe_json().with_return_materializers(
        PandasJSONMaterializer
    ),
    step_3_1=last_step_1(),
    step_3_2=last_step_2(),
)

# needed for airflow
DAG = split_pipeline.run()
