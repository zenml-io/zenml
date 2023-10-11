---
description: Overview of categories of MLOps components.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# 📜 Component Guide

If you are new to the world of MLOps, it is often daunting to be immediately faced with a sea of tools that seemingly
all promise and do the same things. It is useful in this case to try to categorize tools in various groups in order to
understand their value in your toolchain in a more precise manner.

ZenML tackles this problem by introducing the concept
of [Stacks and Stack Components](/docs/book/user-guide/starter-guide/understand-stacks.md). These stack components represent
categories, each of which has a particular function in your MLOps pipeline. ZenML realizes these stack components as
base abstractions that standardize the entire workflow for your team. In order to then realize the benefit, one can
write a concrete implementation of
the [abstraction](/docs/book/platform-guide/set-up-your-mlops-platform/implement-a-custom-stack-component.md), or use 
one of the many built-in [integrations](integration-overview.md) that implement these abstractions for you.

Here is a full list of all stack components currently supported in ZenML, with a description of the role of that
component in the MLOps process:

| **Type of Stack Component**                                            | **Description**                                                   |
|------------------------------------------------------------------------| ----------------------------------------------------------------- |
| [Orchestrator](orchestrators/orchestrators.md)                         | Orchestrating the runs of your pipeline                           |
| [Artifact Store](artifact-stores/artifact-stores.md)                   | Storage for the artifacts created by your pipelines               |
| [Container Registry](container-registries/container-registries.md)     | Store for your containers                                         |
| [Secrets Manager](secrets-managers/secrets-managers.md) (deprecated)   | Centralized location for the storage of your secrets              |
| [Step Operator](step-operators/step-operators.md)                      | Execution of individual steps in specialized runtime environments |
| [Model Deployer](model-deployers/model-deployers.md)                   | Services/platforms responsible for online model serving           |
| [Feature Store](feature-stores/feature-stores.md)                      | Management of your data/features                                  |
| [Experiment Tracker](experiment-trackers/experiment-trackers.md)       | Tracking your ML experiments                                      |
| [Alerter](alerters/alerters.md)                                        | Sending alerts through specified channels                         |
| [Annotator](annotators/annotators.md)                                  | Labeling and annotating data                                      |
| [Data Validator](data-validators/data-validators.md)                   | Data and model validation                                         |
| [Image Builder](image-builders/image-builders.md)                      | Builds container images.                                          |
| [Model Registry](model-registries/model-registries.md)                 | Manage and interact with ML Models                                |

Each pipeline run that you execute with ZenML will require a **stack** and each **stack** will be required to include at
least an orchestrator and an artifact store. Apart from these two, the other components are optional and to be added as
your pipeline evolves in MLOps maturity.
