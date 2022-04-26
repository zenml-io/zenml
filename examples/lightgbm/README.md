# Gradient Boosting with LightGBM and ZenML

[LightGBM](https://lightgbm.readthedocs.io/en/latest/) is an optimized distributed gradient boosting library designed to be highly efficient, flexible and portable. It implements machine learning algorithms under the Gradient Boosting framework. LightGBM provides a parallel tree boosting (also known as GBDT, GBM) that solve many data science problems in a fast and accurate way. 

This example showcases how to train a `lightgbm.Booster` model in a ZenML pipeline. The ZenML `LightGBM` integration includes a custom materializer that persists the trained `lightgbm.Booster` model to and from the artifact store. It also includes materializers for the custom `LightGBM.Dataset` data object.

The data used in this example is the quickstart LightGBM data and is available in the [simple Python example of the LightGBM repository](https://github.com/microsoft/LightGBM/blob/master/examples/python-guide/simple_example.py).

## Run it locally

### Pre-requisites
In order to run this example, you need to install and initialize ZenML:

```shell
# install CLI
pip install zenml

# install ZenML integrations
zenml integration install lightgbm -f

# pull example
zenml example pull lightgbm
cd zenml_examples/lightgbm

# initialize
zenml init
```

### Run the project
Now we're ready. Execute:

```shell
python run.py
```

### Clean up
In order to clean up, delete the remaining ZenML references.

```shell
rm -rf zenml_examples
```

## SuperQuick `lightgbm` run

If you're really in a hurry and you want just to see this example pipeline run,
without wanting to fiddle around with all the individual installation and
configuration steps, just run the following:

```shell
zenml example run lightgbm
```
