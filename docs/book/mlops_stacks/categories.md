---
description: Overview of categories of MLOps tools
---

# Breaking down MLOps into Digestible Categories

(TBD: Insert picture of categories)

If you are new to the world of MLOps, it is often daunting to be immediately faced 
with a sea of tools that seemingly all promise and do the same things. It is useful 
in this case to try to categorize tools in various groups in order to understand 
their value in your tool chain in a more precise manner.

ZenML tackles this problem by introducing [Stack](../developer-guide/stacks-profiles-repositories/stacks_profiles_repositories.md) 
that are composed of **Stack Components**. These stack component represent categories, each of which 
has a particular function in your MLOps pipeline. ZenML realizes these stack components as base abstractions 
that standardize the entire workflow for your team. In order to then realize benefit, one can write a 
[concrete implementation](../developer-guide/advanced-concepts/) of the abstraction, or 
use one of the many built-in [integrations](integrations.md) that implement these abstractions for you.

This is a full list of all stack components currently supported in ZenML, with a description 
of that components role in the MLOps process:

| **Type of Stack Component**                 | **Description**                                                   |
|---------------------------------------------|-------------------------------------------------------------------|
| [Orchestrator](orchestrators/overview.md)             | Orchestrating the runs of your pipeline                           |
| [Artifact Store](artifact-stores/overview.md)         | Storage for the artifacts created by your pipelines               |
| [Metadata Store](metadata-stores/overview.md)         | Tracking the execution of your pipelines/steps                    |
| [Container Registry](container-registries/overview.md) | Store for your containers                                         |
| [Secrets Manager](secrets-managers/overview.md)       | Centralized location for the storage of your secrets              |
| [Step Operator](step-operators/overview.md)           | Execution of individual steps in specialized runtime environments |
| [Model Deployer](model-deployers/overview.md)         | Services/platforms responsible for online model serving           |
| [Feature Store](feature-stores/overview.md)           | Management of your data/features                                  |
| [Experiment Tracker](experiment-trackers/overview.md) | Tracking your ML experiments                                      |
| [Alerter](alerters/overview.md)                       | Sending alerts through specified channels                         |

Ech pipeline run that you execute with ZenML will require a **stack** and each **stack** will be required to include at least an orchestrator, an artifact store, and a metadata store. Apart from these three, the other components are optional and to be added as your pipeline evolves in 
MLOps maturity.

In the upcoming sections, you will learn about each stack component, its role in further detail, and how to use them in 
your own ZenML pipelines.