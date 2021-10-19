---
description: Bringing Zen into ML(Ops)
---

# Why ZenML?

## What is so special about ZenML?

While there are other workflow orchestration tools, ZenML is built because we wanted the following:

- We wanted a tool that is **flexible**: Simple Python functions can be converted into a workflow step.
- We wanted a tool that is **simple:** You can run it locally and with a few commands can get it running on the cloud with minimum changes.
- We wanted to created a **machine learning specific** workflow tool: With ML, workflows need to focus not just on tasks, but also data like models, parameters, statistics and other ML-specific artifacts. This way we can solve machine learning specific problems and create a more understandable API.
- We wanted a tool that can **integrate** with the exploding ML/MLOps landscape: It is so confusing right now because every team that is doing serious ML has their own way of doing things. This is completely fine, but we built ZenML to be a connector and gateway to many other amazing tools for specific problems in machine learning.

In addition, ZenML uses the following modern concepts in pipeline design to bring the latest best practices to MLOps:

## Pipelines As Experiments (PaE)

We built ZenML because we could not find an easy framework that translates the patterns observed in the research phase with Jupyter notebooks into a production-ready ML environment. ZenML follows the paradigm of Pipelines as Experiments (PaE), meaning ZenML pipelines are designed to be written early on the development lifecycle, where the users can explore their pipelines as they develop towards production.

## Developer Experience (DX)

Modern developer experience has been refined past the point of . ZenML is built to give developers a similar experience as other awesome frameworks in other domains like [HuggingFace](https://huggingface.co) and [PyTorch Lightning](https://www.pytorchlightning.ai), but geared towards MLOps.

## Data-centric Pipelines

Going from model-centric to data-centric AI has been a theme of the last years, popularized by Andrew Ng (see video below). ZenML is built with data-centric pipelines in mind. Concretely, this means:

- It allows defining data flow pipelines, rather than task dependencies \[Read this [awesome post](https://rillabs.org/posts/workflows-dataflow-not-task-deps) by RIL Labs to see why that matters]
- It allows developers to explore data artifacts natively in interactive environments.
- It exposes first class data comparison mechanisms, and tracks relevant metadata automatically.

{% embed url="https://www.youtube.com/watch?v=06-AZXmwHjo" %}

## The Right Abstractions

While there are other pipelining solutions for Machine Learning experiments, **ZenML** is focused on the following:

- Simplicity.
- Reproducibility.
- Integrations.

Why we think this is the right abstraction layer (read more coming soon).

Too complicated:

- Dagster
- Flyte
- Metaflow
- Prefect

Too little ops:

- MLFlow
- Kedro

## The Modular MLOps Stack: Integrations

Integrating with others is an important piece that many orchestrators seem to miss \[coming soon]
