---
description: A simple example to get started with ZenML
---

# ZenML Quickstart Guide

Our goal here is to help you to get the first practical experience with our tool and give you a brief overview on some basic functionalities of ZenML.

The quickest way to get started is to create a simple pipeline. We'll be using the [MNIST](http://yann.lecun.com/exdb/mnist/) dataset (originally developed by Yann LeCun and others) digits, and then later the [Fashion MNIST](https://github.com/zalandoresearch/fashion-mnist) dataset developed by Zalando.

If you want to run this notebook in an interactive environment, feel free to run it in a Google Colab.

## Purpose

This quickstart guide is designed to provide a practical introduction to some of the main concepts and paradigms used by the ZenML framework. If you want more detail, our [full documentation](https://docs.zenml.io/) provides more on the concepts and how to implement them.

## Using Google Colab

You will want to use a GPU for this example. If you are following this quickstart in Google's Colab, follow these steps:

- Before running anything, you need to tell Colab that you want to use a GPU. You can do this by clicking on the ‘Runtime’ tab and selecting ‘Change runtime type’. A pop-up window will open up with a drop-down menu.
- Select ‘GPU’ from the menu and click ‘Save’.
- It may ask if you want to restart the runtime. If so, go ahead and do that.

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

## Import relevant packages

We will use pipelines and steps in to train our model.

```python
from zenml import pipelines
from zenml import steps

import tensorflow as tf
```

## Define ZenML Steps

In the code that follows, you can see that we are defining the various steps of our pipeline. Each step is decorated with `@steps.SimpleStep`, the main abstraction that is currently available for creating pipeline steps.

```python
@steps.SimpleStep
def ImportDataStep(dataset):
  # download the MNIST data
  # store it as an artifact
  data = dataset.load_data()

@steps.SimpleStep
def TrainTestSplitStep(dataset):
  (train_images, train_labels), (test_images, test_labels) = dataset

@steps.SimpleStep
def NormalizeDataStep(train_images, test_images):
  # normalize the values for all the images so they are
  # between 0 and 1
  train_images = train_images / 255.0
  test_images = test_images / 255.0

@steps.SimpleStep
def MNISTTrainModelStep(train_data, test_data):
  # train a neural net from scratch to recognise MNIST digits
  # return out model or the learner
  model = tf.keras.models.Sequential([
    tf.keras.layers.Flatten(input_shape=(28, 28)),
    tf.keras.layers.Dense(128,activation='relu'),
    tf.keras.layers.Dense(10)
  ])

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

@steps.SimpleStep
def EvaluateModelStep(model):
  # visualise the loss for the model for each epoch in a graph?
  test_loss, test_acc = model.evaluate(test_images,  test_labels, verbose=2)
```

## Define ZenML Pipeline

A pipeline is defined with the `@pipelines.SimplePipeline` decorator. This defines the various steps of the pipeline and specifies the order in which they will be run.

```python
# Define the pipeline

@pipelines.SimplePipeline
def MNISTTrainingPipeline(import_data: Step[ImportDataStep],
                          train_test_split: Step[TrainTestSplitStep],
                          normalize_data: Step[NormalizeDataStep],
                          trainer: Step[MNISTTrainModelStep],
                          evaluator: Step[EvaluateModelStep]):
  # takes all the steps, in order
  # runs them on the local machine
```

## Initialize a Pipeline Instance

Here we initialize an instance of our `MNISTTrainingPipeline`, passing in the URI for the dataset we wish to download. In our case this is the MNIST digits dataset.

```python
# Initialize the pipeline

mnist_data = tf.keras.datasets.mnist

mnist_trainer = MNISTTrainingPipeline(
    import_data=ImportDataStep(mnist_data),
    normalize_data=NormalizeDataStep(),
    train_test_split=TrainTestSplitStep(),
    trainer=MNISTTrainModelStep(),
    evaluator=EvaluateModelStep())
```

## Run the Pipeline

Running the pipeline is as simple as calling the `run()` method on the defined pipeline.

```python
mnist_trainer.run()
```

## From MNIST to Fashion MNIST

We got pretty good results on the MNIST model that we trained, but maybe we want to see how a similar training pipeline would work on a different dataset.

You can see how easy it is to switch out one data import step and processing for another in our pipeline.

```python
# Define a new modified step for training our Fashion MNIST model

@steps.SimpleStep
def FashionMNISTTrainModelStep(train_data, test_data):
  # train a neural net from scratch to recognise MNIST digits
  # return out model or the learner
  model = tf.keras.Sequential([
    tf.keras.layers.Flatten(input_shape=(28, 28)),
    tf.keras.layers.Dense(128, activation='relu'),
    tf.keras.layers.Dense(10)
])

  model.compile(optimizer='adam',
              loss=tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True),
              metrics=['accuracy'])

  model.fit(train_data, epochs=10, validation_data=test_data)

# Initialise a new pipeline

fashion_mnist_data = tf.keras.datasets.fashion_mnist

fashion_mnist_trainer = MNISTTrainingPipeline(
    import_data=ImportDataStep(fashion_mnist_data),
    normalize_data=NormalizeDataStep(),
    train_test_split=TrainTestSplitStep(),
    trainer=FashionMNISTTrainModelStep(),
    evaluator=EvaluateModelStep())

# Run the new pipeline

fashion_mnist_trainer.run()
```

… and that's it for the quickstart. If you came here without a hiccup, you must have successly installed ZenML, set up a ZenML repo, configured a training pipeline, executed it and evaluated the results. And, this is just the tip of the iceberg on the capabilities of ZenML.

However, if you had a hiccup or you have some suggestions/questions regarding our framework, you can always check [our docs](https://docs.zenml.io/) or [our github](https://github.com/zenml-io/zenml) or even better join us on [our Slack channel](https://zenml.io/slack-invite).

Cheers!

For more detailed information on all the components and steps that went into this short example, please continue reading [our more detailed documentation pages](https://docs.zenml.io/).
