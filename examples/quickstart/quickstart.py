from typing import List

import numpy as np
import tensorflow as tf

from zenml import step
from zenml.annotations import Output, Input, Step
from zenml.artifacts import ModelArtifact
from zenml.pipelines import pipeline


@step
def ImportDataStep() -> List[np.array]:
    """Download the MNIST data store it as an artifact"""
    (X_train, y_train), (X_test, y_test) = tf.keras.datasets.mnist.load_data()
    return [X_train, X_test, y_train, y_test]


@step
def NormalizeDataStep(X_train: np.array, X_test: np.array) -> List[np.array]:
    """Normalize the values for all the images so they are between 0 and 1"""
    return [X_train / 255.0, X_test / 255]


@step
def MNISTTrainModelStep(
    X_train: np.array,
    y_train: np.array,
    model_artifact: Output[ModelArtifact],
    epochs: int = 10,
):
    """Train a neural net from scratch to recognise MNIST digits return our
    model or the learner"""
    model = tf.keras.models.Sequential(
        [
            tf.keras.layers.Flatten(input_shape=(28, 28)),
            tf.keras.layers.Dense(128, activation="relu"),
            tf.keras.layers.Dense(10),
        ]
    )

    model.compile(
        optimizer=tf.keras.optimizers.Adam(0.001),
        loss=tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True),
        metrics=[tf.keras.metrics.SparseCategoricalAccuracy()],
    )

    model.fit(
        X_train,
        y_train,
        epochs=epochs,
    )

    # write model
    model_artifact.write(model)


@step
def EvaluateModelStep(
    X_test: np.array, y_test: np.array, model_artifact: Input[ModelArtifact]
) -> List[float]:
    """Calculate the loss for the model for each epoch in a graph"""
    model = model_artifact.read()
    test_loss, test_acc = model.evaluate(X_test, y_test, verbose=2)
    return [test_loss, test_acc]


# Define the pipeline


@pipeline
def MNISTTrainingPipeline(
    import_data: Step[ImportDataStep],
    normalize_data: Step[NormalizeDataStep],
    trainer: Step[MNISTTrainModelStep],
    evaluator: Step[EvaluateModelStep],
):
    # Link all the steps artifacts together
    normalize_data(
        X_train=import_data.outputs["return_outputs"][0],
        X_test=import_data.outputs["return_outputs"][2],
    )
    trainer(
        X_train=normalize_data.outputs["return_outputs"][0],
        y_train=normalize_data.outputs["return_outputs"][1],
    )
    evaluator(model_artifact=trainer.outputs["model_artifact"])


# Initialise the pipeline
mnist_pipeline = MNISTTrainingPipeline(
    import_data=ImportDataStep(),
    normalize_data=NormalizeDataStep(),
    trainer=MNISTTrainModelStep(epochs=10),
    evaluator=EvaluateModelStep(),
)


# Run the pipeline
mnist_pipeline.run()
