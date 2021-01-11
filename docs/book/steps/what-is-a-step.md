---
description: Extend ZenML with your own steps
---

# What is a step?

Conceptually, a `Step` in a ZenML pipeline is a discrete and independent part of a pipeline that is responsible for one particular aspect of data manipulation inside a [ZenML pipeline](../pipelines/what-is-a-pipeline.md). For example, a `SplitStep` is responsible for splitting the data into various split's like `train` and `eval` for downstream steps to then use.

A ZenML installation already comes with many `standard` steps found in `zenml.core.steps.*` for users to get started. However, it is easy and intended for users to extend these steps or even create steps from scratch as it suits their needs.

### Relation to TFX Components

Most standard steps are currently higher-level abstractions to[ TFX components](https://github.com/tensorflow/tfx/tree/master/tfx/components), just like ZenML pipelines are higher-level abstractions of TFX pipelines.

