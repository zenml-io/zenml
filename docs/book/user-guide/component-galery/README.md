---
description: Overview of categories of MLOps components.
---

# 📜 Component Guide

If you are new to the world of MLOps, it is often daunting to be immediately faced with a sea of tools that seemingly all promise and do the same things. It is useful in this case to try to categorize tools in various groups in order to understand their value in your toolchain in a more precise manner.

ZenML tackles this problem by introducing the concept of [Stacks and Stack Components](../../../old\_book/advanced-guide/stacks/stacks.md). These stack components represent categories, each of which has a particular function in your MLOps pipeline. ZenML realizes these stack components as base abstractions that standardize the entire workflow for your team. In order to then realize the benefit, one can write a concrete implementation of the [abstraction](../../book/platform-guide/set-up-your-mlops-platform/custom-flavors.md), or use one of the many built-in [integrations](../../learning/component-gallery/integrations.md) that implement these abstractions for you.

Here is a full list of all stack components currently supported in ZenML, with a description of the role of that component in the MLOps process:

| **Type of Stack Component**                                                                           | **Description**                                                   |
| ----------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| [Orchestrator](../../learning/component-gallery/orchestrators/orchestrators.md)                       | Orchestrating the runs of your pipeline                           |
| [Artifact Store](../../learning/component-gallery/artifact-stores/artifact-stores.md)                 | Storage for the artifacts created by your pipelines               |
| [Container Registry](../../learning/component-gallery/container-registries/container-registries.md)   | Store for your containers                                         |
| [Secrets Manager](../../learning/component-gallery/secrets-managers/secrets-managers.md) (deprecated) | Centralized location for the storage of your secrets              |
| [Step Operator](../../learning/component-gallery/step-operators/step-operators.md)                    | Execution of individual steps in specialized runtime environments |
| [Model Deployer](../../learning/component-gallery/model-deployers/model-deployers.md)                 | Services/platforms responsible for online model serving           |
| [Feature Store](../../learning/component-gallery/feature-stores/feature-stores.md)                    | Management of your data/features                                  |
| [Experiment Tracker](../../learning/component-gallery/experiment-trackers/experiment-trackers.md)     | Tracking your ML experiments                                      |
| [Alerter](../../learning/component-gallery/alerters/alerters.md)                                      | Sending alerts through specified channels                         |
| [Annotator](../../learning/component-gallery/annotators/annotators.md)                                | Labeling and annotating data                                      |
| [Data Validator](../../learning/component-gallery/data-validators/data-validators.md)                 | Data and model validation                                         |
| [Image Builder](../../learning/component-gallery/image-builders/image-builders.md)                    | Builds container images.                                          |
| [Model Registry](../../learning/component-gallery/model-registries/model-registries.md)               | Manage and interact with ML Models                                |

Each pipeline run that you execute with ZenML will require a **stack** and each **stack** will be required to include at least an orchestrator and an artifact store. Apart from these two, the other components are optional and to be added as your pipeline evolves in MLOps maturity.
