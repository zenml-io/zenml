import numpy as np
import tensorflow as tf
from neptune.new.integrations.tensorflow_keras import NeptuneCallback

from zenml.integrations.neptune.experiment_trackers import (
    NeptuneExperimentTrackerSettings,
)
from zenml.integrations.neptune.experiment_trackers.run_state import (
    get_neptune_run,
    neptune_step,
)
from zenml.integrations.tensorflow.materializers.keras_materializer import (
    KerasMaterializer,
)
from zenml.steps import BaseParameters, step


class TrainerParameters(BaseParameters):
    """Trainer params"""

    epochs: int = 1
    lr: float = 0.001


settings = NeptuneExperimentTrackerSettings(tags={"keras", "mnist"})


@neptune_step
@step(
    enable_cache=False,
    output_materializers=KerasMaterializer,
    settings={"experiment_tracker.neptune": settings},
)
def tf_trainer(
    params: TrainerParameters,
    x_train: np.ndarray,
    y_train: np.ndarray,
) -> tf.keras.Model:
    """Train a neural net from scratch to recognize MNIST digits return our
    model or the learner"""
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
