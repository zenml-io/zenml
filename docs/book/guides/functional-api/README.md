---
description: Build production ML pipelines from the simple step interface.
---

# Functional API

The Functional ZenML API is defined by the primitive `@step` and `@pipeline` decorators. These make it easy to quickly take your functional code into a zenml pipeline. If you want more control over the different steps the [Class based API](../class-based-api/)  is the way to go.&#x20;

A user may also mix-and-match the Functional API with the Class Based API: All standard data types and steps that are applicable in both of these approaches.

In order to illustrate how the Functional API functions, we'll do a simple exercise to create a training pipeline from scratch (without any High Level components) and take it all the way to deployment.

Here is what we'll do in this guide:

* Create a MNIST pipeline that trains using [TensorFlow (Keras)](https://www.tensorflow.org) (similar to the [Quickstart](../../quickstart-guide.md)).
* Swap out implementations of the `trainer` and `evaluator` steps with [scikit-learn](https://scikit-learn.org).
* Persist our interim data artifacts in SQL tables rather than on files.
* Read from a dynamically changing datasource rather than a static one.
* Deploy the pipeline on [Kubeflow Pipelines](https://www.kubeflow.org/docs/components/pipelines/introduction/).

If you just want to see all of the code for each chapter of the guide, head over to the [GitHub version](https://github.com/zenml-io/zenml/tree/main/examples/low\_level\_guide)

If not, then get your environment ready and follow along!

## Set up locally

In order to run the chapters of the guide, you need to install and initialize ZenML:

```bash
pip install zenml 
zenml integration install tensorflow
zenml integration install sklearn
pip install sqlalchemy 

# pull example
zenml example pull low_level_guide
cd zenml_examples/low_level_guide

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
