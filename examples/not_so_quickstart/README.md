# Leverage modular pipelines and caching
This example builds on the [quickstart](../quickstart) but showcases how easy ZenML makes it to swap out different steps within a pipeline, as long as the interfaces remain the same.

We'll be using the [MNIST](http://yann.lecun.com/exdb/mnist/) dataset (originally developed by Yann LeCun and others) digits and train a classifier using [Tensorflow (Keras)](https://www.tensorflow.org/), [PyTorch](https://pytorch.org/), and [scikit-learn](https://scikit-learn.org/).

If you want to run this notebook in an interactive environment, feel free to run it in a [Google Colab version](https://colab.research.google.com/github/zenml-io/zenml/blob/main/examples/not_so_quickstart/not_so_quickstart.ipynb).

## Overview
Here we swap out the `trainer` and `evaluator` steps of the MNIST pipeline with different implementations. The advantage is:

* One can separate ingestion and pre-processing from the actual training: Here we consume for a tensorflow dataset but train it on sci-kit and pytorch.
* We need only run the ingestion and pre-processing steps once, then they are cached for subsequent runs. You will notice when you run this that the first pipeline run takes a bit of time, but then the second and third are faster to get to the trainer!

## Run it locally

### Pre-requisites
In order to run this example, you need to install and initialize ZenML:

```shell
# install CLI
pip install zenml

# install ZenML integrations
zenml integration install tensorflow
zenml integration install torch
zenml integration install sklearn

# pull example
zenml example pull not_so_quickstart
cd zenml_examples/not_so_quickstart

# initialize
git init
zenml init
```

### Run the project
Now we're ready. Execute:

```bash
python run.py
```

### Clean up
In order to clean up, delete the remaining zenml references.

```shell
rm -rf zenml_examples
```