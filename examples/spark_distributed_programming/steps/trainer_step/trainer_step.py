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


from pyspark.ml import Model
from pyspark.ml.classification import RandomForestClassifier
from pyspark.sql import DataFrame

from zenml import step
from zenml.client import Client

step_operator = Client().active_stack.step_operator


@step(step_operator=step_operator.name)
def trainer_step(dataset: DataFrame) -> Model:
    rf = RandomForestClassifier(
        featuresCol="data_xf", labelCol="label", numTrees=10
    )
    return rf.fit(dataset)
