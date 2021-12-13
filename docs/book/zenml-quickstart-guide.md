---
description: Get up and running quickly.
---

# ZenML Quickstart Guide

Our goal here is to help you to get the first practical experience with our tool and give you a brief overview on some basic functionalities of ZenML.

The quickest way to get started is to create a simple pipeline. We'll be using the [MNIST](http://yann.lecun.com/exdb/mnist/) dataset \(originally developed by Yann LeCun and others\) digits, and then later the [Fashion MNIST](https://github.com/zalandoresearch/fashion-mnist) dataset developed by Zalando.

If you want to run this notebook in an interactive environment, feel free to run it in a [Google Colab](https://colab.research.google.com/github/zenml-io/zenml/blob/main/examples/quickstart/quickstart.ipynb), or see the code in GitHub [directly](https://github.com/zenml-io/zenml/tree/main/examples/quickstart).

## Step 0: Install ZenML and Tensorflow

```text
pip install zenml tensorflow
```

## Step 1: Initialize git and zenml repository 

Once the installation is completed, you can go ahead and create your first ZenML repository for your project. As ZenML repositories are built on top of Git repositories, you can create yours in a desired empty directory.

```bash
git init
zenml init
```

Now, the setup is completed. For the next steps, just make sure that you are executing the code within your ZenML repository.

## Step 2: Import relevant packages

We will use pipelines and steps in to train our model:

```python
from typing import List

import numpy as np 
import tensorflow as tf

from zenml.annotations import Input, Output, Step
from zenml.artifacts import DataArtifact, ModelArtifact
from zenml.pipelines import pipeline
from zenml.steps import step
```

## Step 3: Define ZenML Steps

In the code that follows, you can see that we are defining the various steps of our pipeline. Each step is decorated with `@step`, the main abstraction that is currently available for creating pipeline steps.

```python
@step(name="import")
def ImportDataStep() -> List[float]:
    """Download the MNIST data store it as an artifact"""
    (X_train, y_train), (
        X_test,
        y_test,
    ) = tf.keras.datasets.mnist.load_data()
    return [
        X_train.tolist()[0:100],
        y_train.tolist()[0:100],
        X_test.tolist()[0:100],
        y_test.tolist()[0:100],
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
```

## Step 4: Define the pipeline

A pipeline is defined with the `@pipeline` decorator. This defines the various steps of the pipeline and specifies the dependencies between the steps, thereby determining the order in which they will be run.

```python
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

```

## Step 5: Run the pipeline

Here we initialize a run of our `MNISTTrainingPipeline:`

```python
# Initialise the pipeline
mnist_pipeline = MNISTTrainingPipeline(
    import_data=ImportDataStep(),
    normalize_data=NormalizeDataStep(),
    trainer=MNISTTrainModelStep(epochs=10),
    evaluator=EvaluateModelStep(),
)

# Run the pipeline
mnist_pipeline.run()
```

## Step 6: Define a new modified import data step to download the Fashion MNIST model

We got pretty good results on the MNIST model that we trained, but maybe we want to see how a similar training pipeline would work on a different dataset.

You can see how easy it is to switch out one data import step and processing for another in our pipeline.

```python
# Define a new modified import data step to download the Fashion MNIST model
@step(name="import_fashion_mnist")
def ImportDataStep() -> List[float]:
    """Download the Fashion MNIST data store it as an artifact"""
    (X_train, y_train), (
        X_test,
        y_test,
    ) = tf.keras.datasets.fashion_mnist.load_data()  # CHANGING to fashion
    return [
        X_train.tolist()[0:100],
        y_train.tolist()[0:100],
        X_test.tolist()[0:100],
        y_test.tolist()[0:100],
    ]
```

## Step 7: Initialise a new pipeline

```python
# Initialise a new pipeline
fashion_mnist_trainer = MNISTTrainingPipeline(
    import_data=ImportDataStep(),
    normalize_data=NormalizeDataStep(),
    trainer=MNISTTrainModelStep(epochs=10),
    evaluator=EvaluateModelStep(),
)
```

## Step 8: Run the new pipeline

```python
# Run the new pipeline
fashion_mnist_trainer.run()
```

… and that's it for the quickstart. If you came here without a hiccup, you must have successly installed ZenML, set up a ZenML repo, configured a training pipeline, executed it and evaluated the results. And, this is just the tip of the iceberg on the capabilities of ZenML.

However, if you had a hiccup or you have some suggestions/questions regarding our framework, you can always check our docs or our github or even better join us on our Slack channel.

Cheers!

