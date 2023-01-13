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

import numpy as np  # type: ignore [import]
import tensorflow as tf  # type: ignore [import]

from zenml.steps import BaseParameters, step


class TensorflowTrainerParameters(BaseParameters):
    """Trainer params."""

    epochs: int = 1
    lr: float = 0.001


@step
def tf_trainer(
    params: TensorflowTrainerParameters,
    x_train: np.ndarray,
    y_train: np.ndarray,
) -> tf.keras.Model:
    """Train a neural net from scratch to recognize MNIST digits return our
    model or the learner."""
    model = tf.keras.Sequential(
        [
            tf.keras.layers.Flatten(input_shape=(28, 28)),
            tf.keras.layers.Dense(10),
        ]
    )

    model.compile(
        optimizer=tf.keras.optimizers.Adam(params.lr),
        loss=tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True),
        metrics=["accuracy"],
    )

    model.fit(
        x_train,
        y_train,
        epochs=params.epochs,
    )

    # write model
    return model
