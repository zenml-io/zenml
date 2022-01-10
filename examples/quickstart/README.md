# Get up and running quickly
Our goal here is to help you to get the first practical experience with our tool and give you a brief overview 
on some basic functionalities of ZenML. We'll create a training pipeline for the 
[MNIST](http://yann.lecun.com/exdb/mnist/) dataset.

If you want to run this notebook in an interactive environment, feel free to run it in a 
[Google Colab](https://colab.research.google.com/github/zenml-io/zenml/blob/main/examples/quickstart/quickstart.ipynb) 
or view it on [GitHub](https://github.com/zenml-io/zenml/tree/main/examples/quickstart) directly.

## Overview
Here we train a simple `tensorflow.keras` classifier on the MNIST dataset.

## Run it locally

### Pre-requisites
In order to run this example, you need to install and initialize ZenML:

```shell
# install CLI
pip install zenml

# install ZenML integrations
zenml integration install tensorflow

# pull example
zenml example pull quickstart
cd zenml_examples/quickstart

# initialize
zenml init
```

### Run the project
Now we're ready. Execute:

```shell
python quickstart.py
```

Or just a jupyter notebook
```bash
jupyter notebook  # jupyter must be installed
```

Or check out a [Google Colab version](https://colab.research.google.com/github/zenml-io/zenml/blob/main/examples/quickstart/quickstart.ipynb) 
to test it out immediately.

### Clean up
In order to clean up, delete the remaining zenml references.

```shell
rm -rf zenml_examples
```