---
description: Overview of categories of MLOps components
---

# 📜 Component Guide

If you are new to the world of MLOps, it is often daunting to be immediately faced with a sea of tools that seemingly all promise and do the same things. It is useful in this case to try to categorize tools in various groups in order to understand their value in your tool chain in a more precise manner.

ZenML tackles this problem by introducing the concept of [Stacks and Stack Components](../../../old\_book/advanced-guide/stacks/stacks.md). These stack component represent categories, each of which has a particular function in your MLOps pipeline. ZenML realizes these stack components as base abstractions that standardize the entire workflow for your team. In order to then realize benefit, one can write a concrete implementation of the [abstraction](../../book/platform-guide/set-up-your-mlops-platform/custom-flavors.md), or use one of the many built-in [integrations](integrations.md) that implement these abstractions for you.

Here is a full list of all stack components currently supported in ZenML, with a description of that components role in the MLOps process:

| **Type of Stack Component**                                                           | **Description**                                                   |
| ------------------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| [Orchestrator](orchestrators/)                                                        | Orchestrating the runs of your pipeline                           |
| [Artifact Store](artifact-stores/)                                                    | Storage for the artifacts created by your pipelines               |
| [Container Registry](container-registries/)                                           | Store for your containers                                         |
| [Secrets Manager](secrets-managers/)                                                  | Centralized location for the storage of your secrets              |
| [Step Operator](step-operators/)                                                      | Execution of individual steps in specialized runtime environments |
| [Model Deployer](model-deployers/)                                                    | Services/platforms responsible for online model serving           |
| [Feature Store](feature-stores/)                                                      | Management of your data/features                                  |
| [Experiment Tracker](experiment-trackers/)                                            | Tracking your ML experiments                                      |
| [Alerter](alerters/)                                                                  | Sending alerts through specified channels                         |
| [Annotator](annotators/)                                                              | Labeling and annotating data                                      |
| [Data Validator](../../learning/component-gallery/data-validators/data-validators.md) | Data and model validation                                         |
| [Image Builder](image-builders/)                                                      | Builds container images.                                          |
| [Model Registry](model-registries/)                                                   | Manage and interact with ML Models                                |

Each pipeline run that you execute with ZenML will require a **stack** and each **stack** will be required to include at least an orchestrator and an artifact store. Apart from these two, the other components are optional and to be added as your pipeline evolves in MLOps maturity.
