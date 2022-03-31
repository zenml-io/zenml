---
description: Build production ML pipelines from the simple step interface.
---

# Class-based API

The class-based ZenML API is defined by the base classes `BaseStep` and `BasePipeline`. These interfaces allow our 
users to maintain a higher level of control while they are creating a step definition and using it within the context 
of a pipeline.

A user may also mix-and-match the Functional API with the Class Based API: All standard data types and steps 
are applicable in both of these approaches.

In order to illustrate how the class-based API functions, we'll do a simple exercise to build our standard 
built-in training pipeline piece-by-piece. Get your environment ready and follow along!

## 💻 Run it locally

### 📃 Pre-requisites

In order to run the chapters of the guide, you need to install and initialize ZenML:

```bash
# install CLI
pip install zenml 

# install ZenML integrations
zenml integration install tensorflow, sklearn

# pull example if you don't have it locally already
zenml example pull class_based_api
cd zenml_examples/class_based_api
```

### 👣 Stepping through the chapters

In general, to run each chapter you can do:

```shell
python chapter_*.py  # for the chapter of your choice
```

Each of the chapters 

### 🧽  Clean up

In order to clean up, delete the remaining zenml references.

```shell
rm -rf zenml_examples
```

## ⚡ SuperQuick `class_based_api` run

If you're really in a hurry and you want just to see this example pipeline run,
without wanting to fiddle around with all the individual installation and
configuration steps, just run the following:

```shell
zenml example run class_based_api
```

Note that this will run the final example in the series of chapters, `chapter_3.py`.
