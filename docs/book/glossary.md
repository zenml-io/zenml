---
description: Key concepts for working with ZenML
---

# Glossary

For your reference, here are brief explanations of some of the core concepts and mental models used when working with ZenML. The list is sorted alphabetically.

## Artifact

Artifacts are the data that power your experimentation and model training. Artifacts are produced by steps, which are then in turn stored in the artifact store.

Artifacts can be of many different types like `TFRecord`s or saved model pickles, depending on what the step produces.

## Artifact Store

An artifact store is a place where artifacts are stored. These artifacts may have been produced by the pipeline, or they may be the data first ingested into a pipeline.

## Backend

Backends are the infrastructure and environments on which your pipelines run. There are different kinds of backends depending on the particular use case. For example, there are orchestrator backends (like Apache Airflow), processing backends (like Google Cloud Dataflow) and training backends (like Google AI Platform).

## CLI

CLI is an acronym for Command Line Interface. This is the tool you install on the computer or environment where you do your development and experimentation.

## DAG

DAG is an acronym for Directed Acyclic Graph.

- Directed, because the nodes of the graph (i.e. the steps of a pipeline), have a sequence. Nodes do not exist as free-standing entities in this way.
- Acyclic, because there must be one (or more) straight paths through the graph from the beginning to the end. It is acyclic because the graph doesn't loop back on itself at any point.
- Graph, because the steps of the pipeline are represented as nodes in a graph.

## Metadata

Metadata are the pieces of information tracked about the pipelines, experiments and configurations that you are are running with ZenML. Metadata are stored inside the Metadata Store.

## Metadata Store

The configuration of each pipeline, step, backend, and produced artifacts are all tracked within the metadata store. The metadata store is an SQL database, and can be `sqlite` or `mysql`.

## Orchestrator

An orchestrator is a special kind of backend that manages the running of each step of the pipeline. Orchestrators administer the actual pipeline runs. You can think of it as the 'root' of any pipeline job that you run during your experimentation.

## Parameter

When we think about steps as functions, we know they receive input in the form of artifacts. We also know that they produce output (also in the form of artifacts, stored in the artifact store). But steps also take parameters. The parameters that you pass into the steps are also (helpfully!) stored in the metadata store. This helps freeze the iterations of your experimentation workflow in time so you can return to them exactly as you ran them.

## Pipeline

An ZenML pipeline is a sequence of tasks that execute in a specific order and yield artifacts. The artifacts are stored within the artifact store and indexed via the metadata store. Each individual task within a pipeline is known as a step. The standard pipelines (like `SimplePipeline`) within ZenML are designed to have easy interfaces to add pre-decided steps, with the order also pre-decided. Other sorts of pipelines can be created as well from scratch.

Pipelines are functions. They are created by using decorators appropriate to the specific use case you have.

The moment it is `run`, a pipeline is converted to an immutable, declarative YAML configuration file, stored in the pipelines directory. These YAML files may be persisted within the `git` repository as well or kept separate.

## Repository

A repository is at the core of all ZenML activity. Every action that can be executed within ZenML must take place within a ZenML repository. ZenML repositories are inextricably tied to git. ZenML creates a .zen folder at the root of your repository to manage your assets and metadata.

## Stack

Stacks are made up of the following three core components:

- An Artifact Store
- A Metadata Store
- An Orchestrator (backend)

A ZenML stack also happens to be a Pydantic `BaseSettings` class, which means that there are multiple ways to use it.

## Step

A step is a single piece or stage of a ZenML pipeline. Steps are responsible for one aspect of processing or interacting with the data / artifacts in the pipeline. ZenML currently implements a `SimpleStep` interface, but there will be other more customised interfaces (layered in a hierarchy) for specialized implementations. For example, broad steps like `SplitStep`, `PreprocesserStep,` `TrainerStep` and so on.

In this way, steps can be thought of as hierarchical. In a later release, you can see how the `TrainerStep` might look like:

```
BaseTrainerStep
│
└───TensorflowBaseTrainer
│   │
│   └───TensorflowFeedForwardTrainer
│
└───PyTorchBaseTrainer
    │
    └───PyTorchFeedForwardTrainer

```

Each layer defines its own special interface that is essentially placeholder functions to override. So, someone looking to create a custom trainer step would subclass the appropriate class based on the user's requirements.
