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

import pandas as pd

from zenml import pipeline
from zenml.steps import step
from zenml.steps.base_step_config import BaseStepConfig
from zenml.steps.step_output import Output


class StepConfig(BaseStepConfig):
    basic_param_1: int = 1
    basic_param_2: str = 2


@step()
def number_returner(
    config: StepConfig,
) -> Output(number=int, non_number=int):
    return Output(
        number=config.basic_param_1 + int(config.basic_param_2),
        non_number="test",
    )


@step()
def import_dataframe(sum: int) -> pd.DataFrame:
    return pd.DataFrame({"sum": sum})


@pipeline()
def my_pipeline(
    step_1: number_returner,
    step_2: import_dataframe,
):
    number, non_number = step_1()
    step_2(sum=number)


# Pipeline
# TODO [HIGH]: Check that the kwargs passed match my_pipeline definition.
split_pipeline = my_pipeline(
    step_1=number_returner(config=StepConfig(basic_param_2="2")),
    step_2=import_dataframe(),
)

# needed for airflow
DAG = split_pipeline.run()
