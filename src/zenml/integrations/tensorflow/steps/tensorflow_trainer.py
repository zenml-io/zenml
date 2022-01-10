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
from typing import List, Tuple

import pandas as pd
import tensorflow as tf

from zenml.steps.step_interfaces.base_trainer_step import (
    BaseTrainerConfig,
    BaseTrainerStep,
)


class TensorflowBinaryClassifierConfig(BaseTrainerConfig):
    """Config class for the tensorflow trainer

    target_column: the name of the label column
    layers: the number of units in the fully connected layers
    input_shape: the shape of the input
    learning_rate: the learning rate
    metrics: the list of metrics to be computed
    epochs: the number of epochs
    batch_size: the size of the batch
    """

    target_column: str
    layers: List[int] = [256, 64, 1]
    input_shape: Tuple[int] = (8,)
    learning_rate: float = 0.001
    metrics: List[str] = ["accuracy"]
    epochs: int = 50
    batch_size: int = 8


class TensorflowBinaryClassifier(BaseTrainerStep):
    """Simple step implementation which creates a simple tensorflow feedforward
    neural network and trains it on a given pd.DataFrame dataset
    """

    def entrypoint(  # type: ignore[override]
        self,
        train_dataset: pd.DataFrame,
        validation_dataset: pd.DataFrame,
        config: TensorflowBinaryClassifierConfig,
    ) -> tf.keras.Model:
        """Main entrypoint for the tensorflow trainer

        Args:
            train_dataset: pd.DataFrame, the training dataset
            validation_dataset: pd.DataFrame, the validation dataset
            config: the configuration of the step
        Returns:
            the trained tf.keras.Model
        """
        model = tf.keras.Sequential()
        model.add(tf.keras.layers.InputLayer(input_shape=config.input_shape))
        model.add(tf.keras.layers.Flatten())

        last_layer = config.layers.pop()
        for i, layer in enumerate(config.layers):
            model.add(tf.keras.layers.Dense(layer, activation="relu"))
        model.add(tf.keras.layers.Dense(last_layer, activation="sigmoid"))

        model.compile(
            optimizer=tf.keras.optimizers.Adam(config.learning_rate),
            loss=tf.keras.losses.BinaryCrossentropy(),
            metrics=config.metrics,
        )

        train_target = train_dataset.pop(config.target_column)
        validation_target = validation_dataset.pop(config.target_column)
        model.fit(
            x=train_dataset,
            y=train_target,
            validation_data=(validation_dataset, validation_target),
            batch_size=config.batch_size,
            epochs=config.epochs,
        )
        model.summary()

        return model
