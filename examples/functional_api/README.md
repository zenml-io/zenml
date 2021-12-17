# Functional API Guide

The Functional ZenML API is defined by the primitive `@step` and `@pipeline` decorators. These should be used when 
the [Class based API](../class_based_api) is too inflexible for the use-case at hand, and one requires more control 
over individual steps and connecting them in pipelines.

A user may also mix-and-match the Functional API with the Class based API: All standard data types and steps that are 
applicable in the Functional API can be used with the Functional API as well!

In order to illustrate how the Functional API functions, we'll do a simple exercise to create a training pipeline from 
scratch (without any Class based components) and take it all the way to deployment.

Here is what we'll do in this guide:

* Create a MNIST pipeline that trains using [TensorFlow (Keras)](https://www.tensorflow.org/) 
(similar to the [Quickstart](../quickstart/README.md)).
* Swap out implementations of the `trainer` and `evaluator` steps with [scikit-learn](https://scikit-learn.org/).
* Persist our interim data artifacts in SQL tables rather than on files.
* Read from a dynamically changing datasource rather than a static one.
* Deploy the pipeline on [Airflow](https://airflow.apache.org/).


## Run it locally

### Pre-requisites
In order to run the chapters of the guide, you need to install and initialize ZenML:

```shell
# install CLI (order matters, please install in this order.)
pip install zenml 

# install ZenML integrations
zenml integration install tensorflow
zenml integration install airflow
pip install sqlalchemy 
zenml integration install sklearn

# pull example
zenml example pull functional_api
cd zenml_examples/functional_api

# initialize
git init
zenml init
```

### Run the project
Now we're ready. Execute:

```shell
python chapter_*.py  # for the chapter of your choice (except the Airflow chapter)
```

Note before executing each chapter, make sure to clean the old chapter artifact and metadata store:

```shell
rm -rf .zen
zenml init  # start again
```

### Clean up
In order to clean up, delete the remaining zenml references.

```shell
rm -rf zenml_examples
```
