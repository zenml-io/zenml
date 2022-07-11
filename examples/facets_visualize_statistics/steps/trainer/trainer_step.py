#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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
import tensorflow as tf

from zenml.steps import step

FEATURE_COLS = [
    "CRIM",
    "ZN",
    "INDUS",
    "CHAS",
    "NOX",
    "RM",
    "AGE",
    "DIS",
    "RAD",
    "TAX",
    "PTRATIO",
    "B",
    "STAT",
]
TARGET_COL_NAME = "target"


@step
def trainer(train_df: pd.DataFrame) -> tf.keras.Model:
    """A simple Keras Model to train on the data."""
    model = tf.keras.Sequential()
    model.add(
        tf.keras.layers.Dense(
            64,
            activation="relu",
            input_shape=(len(FEATURE_COLS),),
        )
    )
    model.add(tf.keras.layers.Dense(64, activation="relu"))
    model.add(tf.keras.layers.Dense(1))

    model.compile(
        optimizer=tf.keras.optimizers.Adam(0.001),
        loss=tf.keras.losses.MeanSquaredError(),
        metrics=["mae"],
    )

    model.fit(train_df[FEATURE_COLS], train_df[TARGET_COL_NAME])

    # write model
    return model
