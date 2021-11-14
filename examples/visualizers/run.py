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


import numpy as np
from zenml.post_execution.visualizers.facet_statistics_visualizer import (
    FacetStatisticsVisualizer,
)
import pandas as pd
import tensorflow as tf

from zenml.pipelines import pipeline
from zenml.steps import step
from zenml.steps.step_output import Output
from zenml.core.repo import Repository


@step
def importer() -> Output(
    X_train=np.ndarray, y_train=np.ndarray, X_test=np.ndarray, y_test=np.ndarray
):
    """Download the MNIST data store it as numpy arrays."""
    (X_train, y_train), (
        X_test,
        y_test,
    ) = tf.keras.datasets.boston_housing.load_data()
    return X_train, y_train, X_test, y_test


@step
def trainer(
    X_train: np.ndarray,
    y_train: np.ndarray,
) -> tf.keras.Model:
    """A simple Keras Model to train on the data."""
    model = tf.keras.Sequential()
    model.add(tf.keras.layers.Dense(64, activation='relu', input_shape=(X_train.shape[1],)))
    model.add(tf.keras.layers.Dense(64, activation='relu'))
    model.add(tf.keras.layers.Dense(1))

    model.compile(
        optimizer=tf.keras.optimizers.Adam(0.001),
        loss=tf.keras.losses.MeanSquaredError(),
        metrics=["mae"],
    )

    model.fit(X_train, y_train)

    # write model
    return model


@step
def evaluator(
    X_test: np.ndarray,
    y_test: np.ndarray,
    model: tf.keras.Model,
) -> float:
    """Calculate the accuracy on the test set"""
    test_acc = model.evaluate(X_test, y_test, verbose=2)
    return test_acc


@pipeline
def boston_housing_pipeline(
    importer,
    trainer,
    evaluator,
):
    """Links all the steps together in a pipeline"""
    X_train, y_train, X_test, y_test = importer()
    model = trainer(X_train=X_train, y_train=y_train)
    evaluator(X_test=X_test, y_test=y_test, model=model)


def convert_np_to_pandas(X, y):
    cols = [
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
        "MEDV",
    ]
    data = {}
    for i in range(0, X.shape[0]):
        for col in cols:
            data[col] = X[i]
        data['target'] = y[i]
    return pd.DataFrame(data)

if __name__ == "__main__":
    # Run the pipeline
    p = boston_housing_pipeline(
        importer=importer(),
        trainer=trainer(),
        evaluator=evaluator(),
    )
    p.run()

    repo = Repository()
    pipe = repo.get_pipelines()[-1]
    importer_outputs = pipe.runs[-1].get_step(name="importer").outputs
    X_train = importer_outputs["X_train"].read()
    X_test = importer_outputs["X_test"].read()
    y_train = importer_outputs["y_train"].read()
    y_test = importer_outputs["y_test"].read()

    train_df = convert_np_to_pandas(X_train, y_train)
    test_df = convert_np_to_pandas(X_test, y_test)



    FacetStatisticsVisualizer().visualize(train_df)
