# Introduction

## What is ZenML?
**ZenML** is an extensible, open-source MLOps framework for using production-ready Machine Learning pipelines - in a simple way. 

## Why do I need ZenML?
ZenML exists to solve the following problems in Machine Learning development. This includes facing difficulties with:

* **Reproducing** training results in production.
* Managing ML **metadata**, including data, code, and model versioning.
* Getting (and keeping) ML models in **production**.
* **Reusing** code/data and reducing waste.
* Maintaining **comparability** between ML models.
* **Scaling ML** training/inference to large datasets.
* Retaining code **quality** alongside development velocity.
* Keeping up with the ML **tooling landscape** in a coherent manner.

## Key Features
If you/your team struggle with ZenML struggle with the above problems, ZenML solves them via:

* Guaranteed reproducibility of your training experiments. Your pipelines are versioned from data to model, experiments automatically tracked and all pipeline configs are declarative by default.
* Automatic tracking of ML metadata. All runs are tracked in a human-readable, immutable, declarative config.
* Version data, code, and models in one simple interface.
* Re-use code and interim artifacts across experiments and users.
* Guaranteed comparability between experiments.
* Ability to quickly switch between local and cloud environments \(e.g. Kubernetes \).
* Easily integrate with all popular tools including Git, Apache Beam, Kubernetes, PyTorch, TensorFlow.

In addition, ZenML provides some goodies on top:

* Built-in and extensible abstractions for all MLOps needs - from distributed processing on large datasets to Cloud-integrations and model serving backends.
* Pre-built helpers to compare and visualize input parameters as well as pipeline results \(e.g. Tensorboard, TFMA, TFDV\).
* Cached pipeline states for faster experiment iterations.

## List of all benefits

## What to do next?
* Get up and running with your first pipeline [with the Quickstart](getting-started/quickstart.md).
* Read more about [core concepts](getting-started/core-concepts.md) to inform your decision about using ZenML.
* Check out how to [convert your old ML code](getting-started/organizing-zenml.md) into ZenML pipelines, or start from scratch with our [tutorials](tutorials/creating-first-pipeline.ipynb)
* If you are working as a team, see how to [collaborate using ZenML in a team setting](repository/team-collaboration-with-zenml.md).
