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
import tensorflow as tf

from zenml.integrations.constants import GRAPHVIZ, TENSORFLOW
from zenml.integrations.graphviz.visualizers.pipeline_run_dag_visualizer import (
    PipelineRunDagVisualizer,
)
from zenml.pipelines import pipeline
from zenml.repository import Repository
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


@step
def evaluator(
    test_df: pd.DataFrame,
    model: tf.keras.Model,
) -> float:
    """Calculate the accuracy on the test set"""
    _, test_acc = model.evaluate(
        test_df[FEATURE_COLS].values,
        test_df[TARGET_COL_NAME].values,
        verbose=2,
    )
    return test_acc


@pipeline(required_integrations=[GRAPHVIZ, TENSORFLOW])
def boston_housing_pipeline(
    importer,
    trainer,
    evaluator,
):
    """Links all the steps together in a pipeline"""
    train_df, test_df = importer()
    model = trainer(train_df=train_df)
    evaluator(test_df=test_df, model=model)


def visualizer_graph():
    repo = Repository()
    pipe = repo.get_pipelines()[-1]
    latest_run = pipe.runs[-1]
    PipelineRunDagVisualizer().visualize(latest_run)
