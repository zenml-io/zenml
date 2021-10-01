---
description: Discuss why ZenML
---

# Why ZenML?

We built ZenML because we could not find an easy framework that translates the patterns observed in the research phase with Jupyter notebooks into a production-ready ML environment. ZenML follows the paradigm of [Pipelines of Experiments \(PaE\),](why-zenml.md#pipelines-as-experiments-pae) meaning ZenML pipelines are designed to be written early on the development lifecycle, where the users can explore their pipelines as they develop towards production.

By using ZenML at the early stages of development, you get the following features:

* **Reproducibility** of training and inference workflows.  __
* Managing ML **metadata**, including versioning data, code, and models.  
* Getting an **overview** of your ML development, with a reliable link between training and deployment.  __
* Maintaining **comparability** between ML models.  
* **Scaling** ML training/inference to large datasets.  __
* Retaining code **quality** alongside development velocity.  
* **Reusing** code/data and reducing waste. 
* Keeping up with the **ML tooling landscape** with standard abstractions and interfaces.

## What is so special about ZenML?

Here, we could dive into an analysis of other similar tools out there, but as these tend to get outdated really quickly, it is not a useful endeavor. We can however list the vision and philosophy behind ZenML:

* We wanted a tool that is **flexible**: Simple python functions can be converted into a workflow step.
* We wanted a tool that is **simple:** You can run it locally and with a few commands can get it running on the cloud with minimum changes.
* We wanted to created a **machine learning specific** workflow tool: With ML, workflows need to focus not just on tasks, but also data like models, parameters, statistics and other ML-specific artifacts. This way we can solve machine learning specific problems and create a more understandable API.
* We wanted a tool that can **integrate** with the exploding ML/MLOps landscape: It is so confusing right now because every team that is doing serious ML has their own way of doing things. This is completely fine, but we built ZenML to be a connector and gateway to many other amazing tools for specific problems in machine learning.

## Pipelines As Experiments \(PaE\)

## Development Experience \(DX\)

## The Right Abstractions

While there are other pipelining solutions for Machine Learning experiments, **ZenML** is focused on the following:

* Simplicity.
* Reproducibility.
* Integrations.

Why we think this is the right abstraction layer \(have to compare with others\)

Too complicated:

* Dagster
* Flyte
* Metaflow
* Prefect

Too little ops:

* MLFlow
* Kedro

## The modular MLOps stack \(Integrations\)

Integrating with others.

