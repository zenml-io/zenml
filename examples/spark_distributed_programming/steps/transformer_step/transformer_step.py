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

from pyspark.ml import Transformer
from pyspark.ml.feature import OneHotEncoder, StandardScaler, VectorAssembler
from pyspark.sql import DataFrame
from pyspark.sql.functions import col

from zenml import step
from zenml.client import Client
from zenml.steps import Output

step_operator = Client().active_stack.step_operator


@step(step_operator=step_operator.name)
def transformer_step(
    train: DataFrame,
) -> Output(train_xf=DataFrame, scaler=Transformer, encoder=Transformer,):
    # Cast the columns to the right types
    for column in train.columns:
        train = train.withColumn(column, col(column).cast("float"))
    train = train.withColumn("label", col("label").cast("int"))

    # Create a column out of the numerical columns
    assembler = VectorAssembler(
        inputCols=[c for c in train.columns if c.startswith("feature_")],
        outputCol="features",
    )
    train = assembler.transform(train)

    # Use a standard scaler on the numerical values
    standard_scaler = StandardScaler(
        inputCol="features", outputCol="features_xf"
    )
    scaler = standard_scaler.fit(train)
    train = scaler.transform(train)

    # One-hot encode the category column
    encoder = OneHotEncoder(inputCols=["category"], outputCols=["category_xf"])
    encoder = encoder.fit(train)
    train = encoder.transform(train)

    # Conduct the final assembly
    assembler = VectorAssembler(
        inputCols=["features_xf", "category_xf"], outputCol="data_xf"
    )
    train = assembler.transform(train)

    return train, scaler, encoder
