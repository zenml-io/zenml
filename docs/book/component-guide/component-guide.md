---
description: Overview of categories of MLOps components.
---

# 📜 Overview

If you are new to the world of MLOps, it is often daunting to be immediately faced with a sea of tools that seemingly all promise and do the same things. It is useful in this case to try to categorize tools in various groups in order to understand their value in your toolchain in a more precise manner.

ZenML tackles this problem by introducing the concept of [Stacks and Stack Components](../user-guide/production-guide/understand-stacks.md). These stack components represent categories, each of which has a particular function in your MLOps pipeline. ZenML realizes these stack components as base abstractions that standardize the entire workflow for your team. In order to then realize the benefit, one can write a concrete implementation of the [abstraction](../how-to/infrastructure-deployment/stack-deployment/implement-a-custom-stack-component.md), or use one of the many built-in [integrations](README.md) that implement these abstractions for you.

Here is a full list of all stack components currently supported in ZenML, with a description of the role of that component in the MLOps process:

| **Type of Stack Component**                                                                                                                              | **Description**                                                   |
| -------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| [Orchestrator](./orchestrators/orchestrators.md)              | Orchestrating the runs of your pipeline                           |
| [Artifact Store](./artifact-stores/artifact-stores.md)          | Storage for the artifacts created by your pipelines               |
| [Container Registry](./container-registries/container-registries.md) | Store for your containers                                         |
| [Step Operator](./step-operators/step-operators.md)            | Execution of individual steps in specialized runtime environments |
| [Model Deployer](./model-deployers/model-deployers.md)          | Services/platforms responsible for online model serving           |
| [Feature Store](./feature-stores/feature-stores.md)            | Management of your data/features                                  |
| [Experiment Tracker](./experiment-trackers/experiment-trackers.md)  | Tracking your ML experiments                                      |
| [Alerter](./alerters/alerters.md)                        | Sending alerts through specified channels                         |
| [Annotator](./annotators/annotators.md)                    | Labeling and annotating data                                      |
| [Data Validator](./data-validators/data-validators.md)          | Data and model validation                                         |
| [Image Builder](./image-builders/image-builders.md)            | Builds container images.                                          |
| [Model Registry](./model-registries/model-registries.md)         | Manage and interact with ML Models                                |

Each pipeline run that you execute with ZenML will require a **stack** and each **stack** will be required to include at least an orchestrator and an artifact store. Apart from these two, the other components are optional and to be added as your pipeline evolves in MLOps maturity.

## Writing custom component flavors

You can take control of how ZenML behaves by creating your own components. This is done by writing custom component `flavors`. To learn more, head over to [the general guide on writing component flavors](../how-to/infrastructure-deployment/stack-deployment/implement-a-custom-stack-component.md), or read more specialized guides for specific component types (e.g. the [custom orchestrator guide](orchestrators/custom.md)).

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
