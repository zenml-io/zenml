---
description: Build production ML pipelines from the simple step interface.
---

# Low Level API

The Low Level ZenML API is defined by the primitive `@step` and `@pipeline` decorators. These should be used when the [High Level API](../high-level-api/) is too inflexible for the use-case at hand, and one requires more control over individual steps and connecting them in pipelines.

A user may also mix-and-match the Low Level API with the High Level API: All standard data types and steps that are applicable in the High Level API can be used with the Low Level API as well!

In order to illustrate how the Low Level API functions, we'll do a simple exercise to create a training pipeline from scratch (without any High Level components) and take it all the way to deployment.

Here is what we'll do in this guide:

* Create a MNIST pipeline that trains using [TensorFlow (Keras)](https://www.tensorflow.org) (similar to the [Quickstart](../../quickstart-guide.md)).
* Swap out implementations of the `trainer` and `evaluator` steps with [scikit-learn](https://scikit-learn.org).
* Persist our interim data artifacts in SQL tables rather than on files.
* Read from a dynamically changing datasource rather than a static one.
* Deploy the pipeline on [Airflow](https://airflow.apache.org).

If you just want to see all of the code for each chapter of the guide, head over to the [GitHub version](https://github.com/zenml-io/zenml/tree/main/examples/low\_level\_guide)

If not, then get your environment ready and follow along!

## Set up locally

In order to run the chapters of the guide, you need to install and initialize ZenML:

```shell
# install CLI (order matters, please install in this order.)
pip install zenml 
pip install tensorflow
pip install apache_airflow==2.2.0
pip install sqlalchemy 
pip install sklearn

# pull example
zenml example pull low_level_guide

# temporary for version <0.5.2
cd zenml_examples
git checkout main

# back to normal
cd low_level_guide

# initialize
git init
zenml init
```

In general, to run each chapter you can do:

```shell
python chapter_*.py  # for the chapter of your choice
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

Press next to start the first chapter!
