---
description: A simple example to get started with ZenML
---

# Quickstart

Our goal here is to help you to get the first practical experience with our tool and give you a brief overview on 
some basic functionalities of ZenML. We'll create a training pipeline for the [MNIST](http://yann.lecun.com/exdb/mnist/) dataset.

If you want to run this notebook in an interactive environment, feel free to run it in a 
[Google Colab](https://colab.research.google.com/github/zenml-io/zenml/blob/main/examples/quickstart/quickstart.ipynb) 
or view it on [GitHub](https://github.com/zenml-io/zenml/tree/main/examples/quickstart) directly.

## Install and initialize

```python
# Install the dependencies for the quickstart
pip install zenml tensorflow
```

{% hint style="success" %}
We are just using TensorFlow for the purposes of illustration; ZenML works with any ML library such as PyTorch, 
HuggingFace, PyTorch Lightning etc.
{% endhint %}

Once the installation is completed, you can go ahead and create your first ZenML repository for your project. As 
ZenML repositories are built on top of Git repositories, you can create yours in a desired empty directory through:

```python
# Initialize ZenML
zenml init
```

Now, the setup is completed. For the next steps, just make sure that you are executing the code within your 
ZenML repository.

## Define ZenML Steps

In the code that follows, you can see that we are defining the various steps of our pipeline. Each step is 
decorated with `@step`, the main low-level abstraction that is currently available for creating pipeline steps.

![Quickstart steps](../assets/quickstart-diagram.png)

```python
import numpy as np
import tensorflow as tf

from zenml.pipelines import pipeline
from zenml.steps import step, Output


@step
def importer() -> Output(
    X_train=np.ndarray, y_train=np.ndarray, X_test=np.ndarray, y_test=np.ndarray
):
    """Download the MNIST data store it as numpy arrays."""
    (X_train, y_train), (X_test, y_test) = tf.keras.datasets.mnist.load_data()
    return X_train, y_train, X_test, y_test


@step
def trainer(
    X_train: np.ndarray,
    y_train: np.ndarray,
) -> tf.keras.Model:
    """A simple Keras Model to train on the data."""
    model = tf.keras.Sequential()
    model.add(tf.keras.layers.Flatten(input_shape=(28, 28)))
    model.add(tf.keras.layers.Dense(10))

    model.compile(
        optimizer=tf.keras.optimizers.Adam(0.001),
        loss=tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True),
        metrics=["accuracy"],
    )

    model.fit(X_train, y_train)

    # write model
    return model


@step
def evaluator(
    X_test: np.ndarray,
    y_test: np.ndarray,
    model: tf.keras.Model,
) -> float:
    """Calculate the accuracy on the test set"""
    test_acc = model.evaluate(X_test, y_test, verbose=2)
    return test_acc


@pipeline
def mnist_pipeline(
    importer,
    trainer,
    evaluator,
):
    """Links all the steps together in a pipeline"""
    X_train, y_train, X_test, y_test = importer()
    model = trainer(X_train=X_train, y_train=y_train)
    evaluator(X_test=X_test, y_test=y_test, model=model)


if __name__ == "__main__":
    # Run the pipeline
    p = mnist_pipeline(
        importer=importer(),
        trainer=trainer(),
        evaluator=evaluator(),
    )
    p.run()
```

{% hint style="info" %}
This code block should work 'as is'. Copy paste it into your IDE and run it!
{% endhint %}

If you had a hiccup or you have some suggestions/questions regarding our framework, you can always check 
[our Github](https://github.com/zenml-io/zenml) or even better join us on 
[our Slack channel](https://zenml.io/slack-invite).

## Wait, how is this useful?

The above code looks like its yet another standard pipeline framework that added to your work, but there is a lot 
going on under the hood that is mighty helpful:

- All data is versioned and tracked as it flows through the steps.
- All parameters and return values are tracked by a central metadata store that you can later query.
- Individual step outputs are now cached, so you can swap out the trainer for other implementations and iterate fast.
- Code is versioned with `git`.

With just a little more work, one can:

- Deploy this pipeline 'in production' on the cloud with a production ready orchestrator like Kubeflow.
- Useful metadata like statistics, schemas and drifts can be inferred from model and data flowing through these steps.
- Convert these steps to run distributed processing to handle large volumes of data.
- Models trained this way can be set up to be easily deployed, run batch inference on, or set up in continuous 
training loops with automatic deployments.

Best of all: We let you and your infra/ops team decide what the underlying tools are to achieve all this.

Keep reading to learn how all of the above can be achieved.

## Next Steps?

Normally at this point in a quickstart, you'd like to learn more about what the product has to offer (if the docs 
have succeeded in making you feel so). There are essentially two choices you can make:

- If your work involves a use-case that is fairly 'standard' training/inference/deployment, start with 
the [Class-based API](../guides/class-based-api/) guide.
- If you have a more complex workflow that requires more control over your pipelines, start with 
the [Functional API](../guides/functional-api/) guide.

If you're not sure, pick any one of the above. They are the easiest way to learn how ZenML enables MLOps.

However, for those of you who don't want to read guides, then feel free to start perusing the docs with 
the [Core Concepts](core-concepts.md) before the guides. See you there!
