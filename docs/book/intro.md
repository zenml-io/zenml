# Introduction

## What is ZenML?

**ZenML** is an extensible, open-source MLOps framework for using production-ready Machine Learning pipelines - in a simple way. 

### Key Features

* Guaranteed reproducibility of your training experiments. Your pipelines are versioned from data to model, experiments automatically tracked and all pipeline configs are declarative by default.
* Guaranteed comparability between experiments.
* Ability to quickly switch between local and cloud environments \(e.g. Kubernetes, Apache Beam\).
* Built-in and extensible abstractions for all MLOps needs - from distributed processing on large datasets to Cloud-integrations and model serving backends.
* Pre-built helpers to compare and visualize input parameters as well as pipeline results \(e.g. Tensorboard, TFMA, TFDV\).
* Cached pipeline states for faster experiment iterations.

**ZenML** is built to take your experiments all the way from data versioning to a deployed model. It replaces fragile glue-code and scripts to automate Jupyter Notebooks for **production-ready Machine Learning**. The core design is centered around **extensible interfaces** to accommodate **complex pipeline** scenarios while providing a **batteries-included, straightforward “happy path”** to achieve success in common use-cases **without unnecessary boiler-plate code**. 

## In a nutshell

### For Data Science people...

For the people who actually create models and do experiments, you get exposed to simple interfaces to plug and play your models and data with. You can run experiments remotely as easily as possible, and use the built-in automatic evaluation mechanisms to analyze precisely what happened. The goal is for you to follow as closely as possible the pandas/numpy/scikit paradigm you are familiar with, but to end-up with production-ready, scalable, and deployable models at the end. Every parameter is tracked and all artifacts are reproducible.

### For Ops people...

For the people who are responsible for managing the infrastructure and tasked with negotiating the ever-changing ML eco-system, ZenML should be seen as a platform that provides high-level integrations to various backends that are tedious to build and maintain. If you want to swap out some components with others, then you are free to do so! For example, if you want to deploy on different cloud providers \(AWS, GCP, Azure\), or a different data processing backend \(Spark, Dataflow, etc\), then ZenML provides this ability natively.

To get started with ZenML, head on over to the [quickstart](getting-started/quickstart.md) to create your first ZenML pipeline.

