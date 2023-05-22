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

from pyspark.sql import DataFrame

from zenml import step
from zenml.client import Client
from zenml.steps import BaseParameters, Output

step_operator = Client().active_stack.step_operator


class SplitParameters(BaseParameters):
    train_ratio: float
    test_ratio: float
    eval_ratio: float


@step(step_operator=step_operator.name)
def split_step(
    dataset: DataFrame, params: SplitParameters
) -> Output(train=DataFrame, test=DataFrame, eval=DataFrame,):
    return dataset.randomSplit(
        [
            params.train_ratio,
            params.test_ratio,
            params.eval_ratio,
        ]
    )
