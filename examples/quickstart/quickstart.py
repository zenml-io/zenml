from typing import List

import numpy as np
import tensorflow as tf

from zenml import step
from zenml.annotations import Output
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
    X_train: np.array, y_train: np.array, model_artifact: Output[ModelArtifact]
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
        train_data,
        epochs=10,
        validation_data=test_data,
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
    train_test_split: Step[TrainTestSplitStep],
    normalize_data: Step[NormalizeDataStep],
    trainer: Step[MNISTTrainModelStep],
    evaluator: Step[EvaluateModelStep],
):
    # takes all the steps, in order
    # runs them on the local machine

    # Initialise the pipeline

    mnist_data = tf.keras.datasets.mnist

    mnist_trainer = MNISTTrainingPipeline(
        import_data=ImportDataStep(mnist_data),
        normalize_data=NormalizeDataStep(),
        train_test_split=TrainTestSplitStep(),
        trainer=MNISTTrainModelStep(),
        evaluator=EvaluateModelStep(),
    )


# Run the pipeline

mnist_trainer.run()
