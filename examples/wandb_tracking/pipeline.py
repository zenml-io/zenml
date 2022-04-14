#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
import os

import numpy as np
import tensorflow as tf
import wandb
from wandb.keras import WandbCallback

from zenml.integrations.constants import TENSORFLOW, WANDB
from zenml.integrations.wandb.wandb_step_decorator import enable_wandb
from zenml.pipelines import pipeline
from zenml.steps import BaseStepConfig, Output, step

WANDB_PROJECT_NAME = os.getenv("WANDB_PROJECT_NAME")
WANDB_ENTITY = os.getenv("WANDB_ENTITY")
WANDB_API_KEY = os.getenv("WANDB_API_KEY")
if WANDB_PROJECT_NAME is None:
    raise AssertionError("Set the env variable WANDB_PROJECT_NAME please!")
if WANDB_API_KEY is None:
    raise AssertionError("Set the env variable WANDB_API_KEY please!")


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
    ) = tf.keras.datasets.mnist.load_data()
    return x_train, y_train, x_test, y_test


@step
def normalizer(
    x_train: np.ndarray, x_test: np.ndarray
) -> Output(x_train_normed=np.ndarray, x_test_normed=np.ndarray):
    """Normalize the values for all the images so they are between 0 and 1"""
    x_train_normed = x_train / 255.0
    x_test_normed = x_test / 255.0
    return x_train_normed, x_test_normed


# Define the step and enable wandb - order of decorators is important here
@enable_wandb(project_name=WANDB_PROJECT_NAME, entity=WANDB_ENTITY)
@step
def tf_trainer(
    config: TrainerConfig,
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_val: np.ndarray,
    y_val: np.ndarray,
) -> tf.keras.Model:
    """Train a neural net from scratch to recognize MNIST digits return our
    model or the learner"""
    model = tf.keras.Sequential(
        [
            tf.keras.layers.Flatten(input_shape=(28, 28)),
            tf.keras.layers.Dense(10),
        ]
    )

    model.compile(
        optimizer=tf.keras.optimizers.Adam(config.lr),
        loss=tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True),
        metrics=["accuracy"],
    )

    model.fit(
        x_train,
        y_train,
        epochs=config.epochs,
        validation_data=(x_val, y_val),
        callbacks=[
            WandbCallback(
                log_evaluation=True,
                validation_steps=16,
                validation_data=(x_val, y_val),
            )
        ],
    )

    # write model
    return model


# Define the step and enable wandb - order of decorators is important here
@enable_wandb(project_name=WANDB_PROJECT_NAME, entity=WANDB_ENTITY)
@step
def tf_evaluator(
    x_test: np.ndarray,
    y_test: np.ndarray,
    model: tf.keras.Model,
) -> float:
    """Calculate the loss for the model for each epoch in a graph"""

    _, test_acc = model.evaluate(x_test, y_test, verbose=2)
    wandb.log({"val_accuracy": test_acc})
    return test_acc


@pipeline(enable_cache=False, required_integrations=[WANDB, TENSORFLOW])
def wandb_example_pipeline(
    importer,
    normalizer,
    trainer,
    evaluator,
):
    # Link all the steps artifacts together
    x_train, y_train, x_test, y_test = importer()
    x_trained_normed, x_test_normed = normalizer(x_train=x_train, x_test=x_test)
    model = trainer(
        x_train=x_trained_normed, y_train=y_train, x_val=x_test, y_val=y_test
    )
    evaluator(x_test=x_test_normed, y_test=y_test, model=model)
