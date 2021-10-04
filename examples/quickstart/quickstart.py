from typing import List

import numpy as np
import tensorflow as tf

from zenml.annotations import Input, Output, Step
from zenml.artifacts import DataArtifact, ModelArtifact
from zenml.pipelines import pipeline
from zenml.steps import step


@step(name="import")
def ImportDataStep() -> List[float]:
    """Download the MNIST data store it as an artifact"""
    (X_train, y_train), (
        X_test,
        y_test,
    ) = tf.keras.datasets.boston_housing.load_data()
    return [
        X_train.tolist(),
        y_train.tolist(),
        X_test.tolist(),
        y_test.tolist(),
    ]


@step(name="normalize")
def NormalizeDataStep(data: Input[DataArtifact]) -> List[float]:
    """Normalize the values for all the images so they are between 0 and 1"""
    import_data = data.materializers.json.read_file()
    X_train_normed = np.array(import_data[0]) / 255.0
    X_test_normed = np.array(import_data[2]) / 255.0
    return [
        X_train_normed.tolist(),
        import_data[1],
        X_test_normed.tolist(),
        import_data[3],
    ]


@step(name="trainer")
def MNISTTrainModelStep(
    data: Input[DataArtifact],
    model_artifact: Output[ModelArtifact],
    epochs: int,
):
    """Train a neural net from scratch to recognise MNIST digits return our
    model or the learner"""
    import_data = data.materializers.json.read_file()
    model = tf.keras.models.Sequential(
        [
            tf.keras.layers.Dense(28, activation="relu"),
            tf.keras.layers.Dense(1, activation="linear"),
        ]
    )

    model.compile(
        optimizer=tf.keras.optimizers.Adam(0.001),
        loss=tf.keras.losses.MeanSquaredError(),
        metrics=[tf.keras.metrics.MeanSquaredError()],
    )

    model.fit(
        import_data[0],
        import_data[1],
        epochs=epochs,
    )

    # write model
    model_artifact.materializers.keras.write_model(model)


@step(name="evaluate")
def EvaluateModelStep(
    data: Input[DataArtifact], model_artifact: Input[ModelArtifact]
) -> List[float]:
    """Calculate the loss for the model for each epoch in a graph"""
    model = model_artifact.materializers.keras.read_model()
    import_data = data.materializers.json.read_file()

    test_loss, test_acc = model.evaluate(
        import_data[2], import_data[3], verbose=2
    )
    return [test_loss, test_acc]


# Define the pipeline


@pipeline("mnist")
def MNISTTrainingPipeline(
    import_data: Step[ImportDataStep],
    normalize_data: Step[NormalizeDataStep],
    trainer: Step[MNISTTrainModelStep],
    evaluator: Step[EvaluateModelStep],
):
    # Link all the steps artifacts together
    normalize_data(data=import_data.outputs.return_output)
    trainer(data=normalize_data.outputs.return_output)
    evaluator(
        data=normalize_data.outputs.return_output,
        model_artifact=trainer.outputs.model_artifact,
    )


# Initialise the pipeline
mnist_pipeline = MNISTTrainingPipeline(
    import_data=ImportDataStep(),
    normalize_data=NormalizeDataStep(),
    trainer=MNISTTrainModelStep(epochs=10),
    evaluator=EvaluateModelStep(),
)


# Run the pipeline
mnist_pipeline.run()
