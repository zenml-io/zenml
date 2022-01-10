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
from datetime import datetime

import mlflow
import numpy as np
import tensorflow as tf

from zenml.integrations.mlflow.mlflow_utils import (
    enable_mlflow,
    local_mlflow_backend,
)
from zenml.pipelines import pipeline
from zenml.steps import BaseStepConfig, Output, step


class TrainerConfig(BaseStepConfig):
    """Trainer params"""

    epochs: int = 1
    lr: float = 0.001


@step
def importer_mnist() -> Output(
    x_train=np.ndarray, y_train=np.ndarray, x_test=np.ndarray, y_test=np.ndarray
):
    """Download the MNIST data store it as an artifact"""
    (x_train, y_train), (
        x_test,
        y_test,
    ) = tf.keras.datasets.fashion_mnist.load_data()
    return x_train, y_train, x_test, y_test


@step
def normalizer(
    x_train: np.ndarray, x_test: np.ndarray
) -> Output(x_train_normed=np.ndarray, x_test_normed=np.ndarray):
    """Normalize the values for all the images so they are between 0 and 1"""
    x_train_normed = x_train / 255.0
    x_test_normed = x_test / 255.0
    return x_train_normed, x_test_normed


@step(enable_cache=False)
def tf_trainer(
    config: TrainerConfig,
    x_train: np.ndarray,
    y_train: np.ndarray,
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

    model.compile(
        optimizer=tf.keras.optimizers.Adam(config.lr),
        loss=tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True),
        metrics=["accuracy"],
    )

    mlflow.tensorflow.autolog()
    model.fit(
        x_train,
        y_train,
        epochs=config.epochs,
    )

    # write model
    return model


@step(enable_cache=False)
def tf_evaluator(
    x_test: np.ndarray,
    y_test: np.ndarray,
    model: tf.keras.Model,
) -> float:
    """Calculate the loss for the model for each epoch in a graph"""

    _, test_acc = model.evaluate(x_test, y_test, verbose=2)
    mlflow.log_metric("val_accuracy", test_acc)
    return test_acc


# Define the pipeline and enable mlflow - order of decorators is important here
@enable_mlflow
@pipeline(enable_cache=False)
def mlflow_example_pipeline(
    importer,
    normalizer,
    trainer,
    evaluator,
):
    # Link all the steps artifacts together
    x_train, y_train, x_test, y_test = importer()
    x_trained_normed, x_test_normed = normalizer(x_train=x_train, x_test=x_test)
    model = trainer(x_train=x_trained_normed, y_train=y_train)
    evaluator(x_test=x_test_normed, y_test=y_test, model=model)


# Initialize a pipeline run
run_1 = mlflow_example_pipeline(
    importer=importer_mnist(),
    normalizer=normalizer(),
    trainer=tf_trainer(config=TrainerConfig(epochs=5, lr=0.0001)),
    evaluator=tf_evaluator(),
)

run_1.run(run_name=f'run_1_{datetime.now().strftime("%d_%h_%y-%H_%M_%S")}')

# Initialize a pipeline run again
run_2 = mlflow_example_pipeline(
    importer=importer_mnist(),
    normalizer=normalizer(),
    trainer=tf_trainer(config=TrainerConfig(epochs=10, lr=0.001)),
    evaluator=tf_evaluator(),
)

run_2.run(run_name=f'run_2_{datetime.now().strftime("%d_%h_%y-%H_%M_%S")}')

print(
    "Now run \n "
    f"`mlflow ui --backend-store-uri {local_mlflow_backend()}` \n"
    "To inspect your experiment runs within the mlflow ui. \n"
    "You can find your runs tracked within the `mlflow_example_pipeline` "
    "experiment. Here you'll also be able to compare the two runs.)"
)
