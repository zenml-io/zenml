---
description: Build production ML pipelines from the simple step interface.
---

# Class-based API

The class-based ZenML API is defined by the base classes `BaseStep` and `BasePipeline`. These interfaces allow our 
users to maintain a higher level of control while they are creating a step definition and using it within the context 
of a pipeline.

A user may also mix-and-match the Functional API with the Class Based API: All standard data types and steps that 
are applicable in both of these approaches.

In order to illustrate how the class-based API functions, we'll do a simple exercise to build our standard 
built-in training pipeline piece-by-piece.

If you just want to see all the code for each chapter of the guide, head over to the 
[GitHub version](https://github.com/zenml-io/zenml/tree/main/examples/class_based_api)

If not, then get your environment ready and follow along!

## Set up locally

In order to run the chapters of the guide, you need to install and initialize ZenML:

```bash
pip install zenml 
zenml integration install tensorflow
zenml integration install sklearn

# pull example
zenml example pull class_based_api
cd zenml_examples/class_based_api

# initialize
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
