---
description: A simple example to get started with ZenML
---

# Quickstart Guide

Our goal here is to help you to get the first practical experience with our tool and give you a brief overview on some basic functionalities of ZenML.

The quickest way to get started is to create a simple pipeline. We'll be using the [MNIST](http://yann.lecun.com/exdb/mnist/) dataset (originally developed by Yann LeCun and others) digits, and then later the [Fashion MNIST](https://github.com/zalandoresearch/fashion-mnist) dataset developed by Zalando.

If you want to run this notebook in an interactive environment, feel free to run it in a [Google Colab](https://colab.research.google.com/github/zenml-io/zenml/blob/main/examples/quickstart/quickstart.ipynb).

## Purpose

This quickstart guide is designed to provide a practical introduction to some of the main concepts and paradigms used by the ZenML framework. If you want more detail, our [full documentation](https://docs.zenml.io) provides more on the concepts and how to implement them.

## Using Google Colab

You will want to use a GPU for this example. If you are following this quickstart in Google's Colab, follow these steps:

* Before running anything, you need to tell Colab that you want to use a GPU. You can do this by clicking on the ‘Runtime’ tab and selecting ‘Change runtime type’. A pop-up window will open up with a drop-down menu.
* Select ‘GPU’ from the menu and click ‘Save’.
* It may ask if you want to restart the runtime. If so, go ahead and do that.

## Install libraries

```python
# Install the ZenML CLI tool
!pip install zenml tensorflow tensorflow_datasets
```

Once the installation is completed, you can go ahead and create your first ZenML repository for your project. As ZenML repositories are built on top of Git repositories, you can create yours in a desired empty directory through:

```python
# Initialize a git repository
!git init

# Initialize ZenML's .zen file
!zenml init
```

Now, the setup is completed. For the next steps, just make sure that you are executing the code within your ZenML repository.

## Define ZenML Steps

In the code that follows, you can see that we are defining the various steps of our pipeline. Each step is decorated with `@step`, the main abstraction that is currently available for creating pipeline steps.

```python
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
) -> tf.keras.Model:
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
    model: tf.keras.Model,
) -> np.ndarray:
    """Calculate the loss for the model for each epoch in a graph"""

    test_loss, test_acc = model.evaluate(X_test, y_test, verbose=2)
    return np.array([test_loss, test_acc])


```

## Define ZenML Pipeline

A pipeline is defined with the `@pipeline` decorator. This defines the various steps of the pipeline and specifies the order in which they will be run.

```python
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
```

## Run the Pipeline with MNIST

Here we initialize an instance of our `mnist_pipeline.`

```python
# Initialise the pipeline
p = mnist_pipeline(
    importer=importer_mnist(),
    normalizer=normalizer(),
    trainer=trainer(config=TrainerConfig(epochs=1)),
    evaluator=evaluator(),
)
p.run()
```

## From MNIST to Fashion MNIST

We got pretty good results on the MNIST model that we trained, but maybe we want to see how a similar training pipeline would work on a different dataset.

You can see how easy it is to switch out one data import step and processing for another in our pipeline.

```python
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
```

… and that's it for the quickstart. If you came here without a hiccup, you must have successly installed ZenML, set up a ZenML repo, configured a training pipeline, executed it and evaluated the results. And, this is just the tip of the iceberg on the capabilities of ZenML.

However, if you had a hiccup or you have some suggestions/questions regarding our framework, you can always check [our docs](https://docs.zenml.io) or [our github](https://github.com/zenml-io/zenml) or even better join us on [our Slack channel](https://zenml.io/slack-invite).

For more detailed information on all the components and steps that went into this short example, please continue reading [our more detailed documentation pages](https://docs.zenml.io).

Cheers!
