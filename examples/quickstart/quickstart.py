import keras
import numpy as np
import tensorflow as tf

from zenml.pipelines import pipeline
from zenml.steps import step
from zenml.steps.base_step_config import BaseStepConfig
from zenml.steps.step_output import Output


class TrainerConfig(BaseStepConfig):
    """Trainer params"""

    epochs: int = 1


@step
def importer_mnist() -> Output(
    X_train=np.ndarray, y_train=np.ndarray, X_test=np.ndarray, y_test=np.ndarray
):
    """Download the MNIST data store it as an artifact"""
    (X_train, y_train), (
        X_test,
        y_test,
    ) = tf.keras.datasets.mnist.load_data()
    return X_train, y_train, X_test, y_test


@step
def normalizer(
    X_train: np.ndarray, X_test: np.ndarray
) -> Output(X_train_normed=np.ndarray, X_test_normed=np.ndarray):
    """Normalize the values for all the images so they are between 0 and 1"""
    X_train_normed = X_train / 255.0
    X_test_normed = X_test / 255.0
    return X_train_normed, X_test_normed


@step
def trainer(
    config: TrainerConfig,
    X_train: np.ndarray,
    y_train: np.ndarray,
) -> keras.Model:
    """Train a neural net from scratch to recognise MNIST digits return our
    model or the learner"""
    model = tf.keras.Sequential(
        [
            tf.keras.layers.Flatten(input_shape=(28, 28)),
            tf.keras.layers.Dense(10, activation="relu"),
            tf.keras.layers.Dense(10),
        ]
    )

    model.compile(
        optimizer=tf.keras.optimizers.Adam(0.001),
        loss=tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True),
        metrics=["accuracy"],
    )

    model.fit(
        X_train,
        y_train,
        epochs=config.epochs,
    )

    # write model
    return model


@step
def evaluator(
    X_test: np.ndarray,
    y_test: np.ndarray,
    model: keras.Model,
) -> np.ndarray:
    """Calculate the loss for the model for each epoch in a graph"""

    test_loss, test_acc = model.evaluate(X_test, y_test, verbose=2)
    return np.array([test_loss, test_acc])


# Define the pipeline


@pipeline
def mnist_pipeline(
    importer,
    normalizer: normalizer,
    trainer,
    evaluator,
):
    # Link all the steps artifacts together
    X_train, y_train, X_test, y_test = importer()
    X_trained_normed, X_test_normed = normalizer(X_train=X_train, X_test=X_test)
    model = trainer(X_train=X_trained_normed, y_train=y_train)
    evaluator(X_test=X_test_normed, y_test=y_test, model=model)


# Initialise the pipeline
p = mnist_pipeline(
    importer=importer_mnist(),
    normalizer=normalizer(),
    trainer=trainer(config=TrainerConfig(epochs=1)),
    evaluator=evaluator(),
)

# Run the pipeline
p.run()


# Define a new modified import data step to download the Fashion MNIST model
@step
def importer_fashion_mnist() -> Output(
    X_train=np.ndarray, y_train=np.ndarray, X_test=np.ndarray, y_test=np.ndarray
):
    """Download the MNIST data store it as an artifact"""
    (X_train, y_train), (
        X_test,
        y_test,
    ) = tf.keras.datasets.fashion_mnist.load_data()
    return X_train, y_train, X_test, y_test


# Initialise a new pipeline
fashion_p = mnist_pipeline(
    importer=importer_fashion_mnist(),
    normalizer=normalizer(),
    trainer=trainer(config=TrainerConfig(epochs=1)),
    evaluator=evaluator(),
)

# Run the new pipeline
fashion_p.run()
