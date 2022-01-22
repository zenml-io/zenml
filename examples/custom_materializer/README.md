# Creating custom materializer

In order.

## Overview
Here we train a simple classifier on the MNIST dataset.

## Run it locally

### Pre-requisites
In order to run this example, you need to install and initialize ZenML:

```shell
# install CLI
pip install zenml

# install ZenML integrations
zenml integration install sklearn

# pull example
zenml example pull custom_materializer
cd zenml_examples/custom_materializer

# initialize
zenml init
```

### Run the project
Now we're ready. Execute:

```shell
python run.py
```

### Clean up
In order to clean up, delete the remaining zenml references.

```shell
rm -rf zenml_examples
```

## SuperQuick `custom_materializer` run

If you're really in a hurry and you want just to see this example pipeline run,
without wanting to fiddle around with all the individual installation and
configuration steps, just run the following:

```shell
zenml example run custom_materializer
```