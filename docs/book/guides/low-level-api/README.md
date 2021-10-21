---
description: Build production ML pipelines from the simple step interface.
---

# Low Level API

The Low Level ZenML API is defined by the primitive `@step` and `@pipeline` decorators. These should be used when the [High Level API](../high-level-api) is too inflexible for the use-case at hand, and when one requires more control over individual steps and connecting them in pipelines.

A user may also mix-and-match the Low Level API with the High Level API: All standard data types and steps that are applicable in the High Level API can be used with the Low Level API as well!

In order to illustrate how the Low Level API functions, we'll do a simple exercise to create a training pipeline from scratch (without any High Level components) and take it all the way to deployment.

Here is what we'll do in this guide:

* Create a MNIST pipeline that trains using [Tensorflow (Keras)](https://www.tensorflow.org/) (similar to the [Quickstart](../../quickstart-guide.md)).
* Swap out implementations of the `trainer` and `evaluator` steps with [scikit-learn](https://scikit-learn.org/).
* Persist our interim data artifacts in SQL tables rather than on files.
* Deploy the pipeline on [Airflow](https://airflow.apache.org/).

If you just want to see the code for the guide, head over to the [GitHub version](https://github.com/zenml-io/zenml/tree/main/examples/low_level_guide)

If not, then press next and let's go through it together!