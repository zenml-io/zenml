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

from zenml.steps import Output, step

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


def convert_np_to_pandas(X, y):
    df = pd.DataFrame(X, columns=FEATURE_COLS)
    df[TARGET_COL_NAME] = y
    return df


@step
def importer() -> Output(train_df=pd.DataFrame, test_df=pd.DataFrame):
    """Download the MNIST data store it as numpy arrays."""
    (X_train, y_train), (
        X_test,
        y_test,
    ) = tf.keras.datasets.boston_housing.load_data()
    train_df = convert_np_to_pandas(X_train, y_train)
    test_df = convert_np_to_pandas(X_test, y_test)
    return train_df, test_df
