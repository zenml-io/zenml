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

import logging
import os

import numpy as np
import tensorflow as tf

from zenml.integrations.constants import TENSORFLOW
from zenml.pipelines import pipeline
from zenml.steps import BaseStepConfig, Output, StepContext, step


@step
def importer() -> Output(
    X_train=np.ndarray,
    X_test=np.ndarray,
    y_train=np.ndarray,
    y_test=np.ndarray,
):
    """Download the MNIST data store it as an artifact"""
    (X_train, y_train), (
        X_test,
        y_test,
    ) = tf.keras.datasets.mnist.load_data()
    return X_train, X_test, y_train, y_test


@step
def normalizer(
    X_train: np.ndarray, X_test: np.ndarray
) -> Output(X_train_normed=np.ndarray, X_test_normed=np.ndarray):
    """Normalize digits dataset with mean and standard deviation."""
    X_train_normed = (X_train - np.mean(X_train)) / np.std(X_train)
    X_test_normed = (X_test - np.mean(X_test)) / np.std(X_test)
    return X_train_normed, X_test_normed


class TrainerConfig(BaseStepConfig):
    """Trainer params"""

    epochs: int = 5
    lr: float = 0.001


@step(enable_cache=True)
def trainer(
    X_train: np.ndarray,
    y_train: np.ndarray,
    context: StepContext,
    config: TrainerConfig,
) -> tf.keras.Model:
    """Train a neural net from scratch to recognize MNIST digits return our
    model or the learner"""
    model = tf.keras.Sequential(
        [
            tf.keras.layers.Flatten(input_shape=(28, 28)),
            tf.keras.layers.Dense(10, activation="relu"),
            tf.keras.layers.Dense(10),
        ]
    )

    log_dir = os.path.join(context.get_output_artifact_uri(), "logs")
    tensorboard_callback = tf.keras.callbacks.TensorBoard(
        log_dir=log_dir, histogram_freq=1
    )

    model.compile(
        optimizer=tf.keras.optimizers.Adam(config.lr),
        loss=tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True),
        metrics=["accuracy"],
    )

    model.fit(
        X_train,
        y_train,
        epochs=config.epochs,
        callbacks=[tensorboard_callback],
    )

    return model


@step
def evaluator(
    X_test: np.ndarray,
    y_test: np.ndarray,
    model: tf.keras.Model,
) -> float:
    """Calculate the accuracy on the test set"""

    _, test_acc = model.evaluate(X_test, y_test, verbose=2)
    logging.info(f"Test accuracy: {test_acc}")
    return test_acc


@pipeline(required_integrations=[TENSORFLOW], enable_cache=True)
def mnist_pipeline(
    importer,
    normalizer,
    trainer,
    evaluator,
):
    # Link all the steps together
    X_train, X_test, y_train, y_test = importer()
    X_trained_normed, X_test_normed = normalizer(X_train=X_train, X_test=X_test)
    model = trainer(X_train=X_trained_normed, y_train=y_train)
    evaluator(X_test=X_test_normed, y_test=y_test, model=model)
