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

import numpy as np
import tensorflow as tf
from neptune.new.integrations.tensorflow_keras import NeptuneCallback

from zenml.client import Client
from zenml.integrations.neptune.experiment_trackers import (
    NeptuneExperimentTracker,
)
from zenml.integrations.neptune.experiment_trackers.run_state import (
    get_neptune_run,
)
from zenml.integrations.neptune.flavors import NeptuneExperimentTrackerSettings
from zenml.integrations.tensorflow.materializers.keras_materializer import (
    KerasMaterializer,
)
from zenml.steps import BaseParameters, step

experiment_tracker = Client().active_stack.experiment_tracker

if not experiment_tracker or not isinstance(
    experiment_tracker, NeptuneExperimentTracker
):
    raise RuntimeError(
        "Your active stack needs to contain a Neptune experiment tracker for "
        "this example to work."
    )


class TrainerParameters(BaseParameters):
    """Trainer params."""

    epochs: int = 1
    lr: float = 0.001


settings = NeptuneExperimentTrackerSettings(tags={"keras", "mnist"})


@step(
    enable_cache=False,
    experiment_tracker=experiment_tracker.name,
    output_materializers=KerasMaterializer,
    settings={"experiment_tracker.neptune": settings},
)
def tf_trainer(
    params: TrainerParameters,
    x_train: np.ndarray,
    y_train: np.ndarray,
) -> tf.keras.Model:
    """Train a neural net from scratch to recognize MNIST digits return our
    model or the learner."""
    neptune_run = get_neptune_run()
    neptune_run["params/lr"] = params.lr

    neptune_cbk = NeptuneCallback(run=neptune_run, base_namespace="metrics")

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
        batch_size=64,
        callbacks=[neptune_cbk],
    )

    return model
