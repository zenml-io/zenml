---
description: Glossary of terminology used in ZenML
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Glossary

## Alerter

Alerters are a type of stack component that allows you to send messages to 
chat services (like Slack, Discord, Mattermost, etc.) from within your 
pipelines. This is useful to immediately get notified when failures happen, 
for general monitoring/reporting, and also for building human-in-the-loop ML.

## Annotator

Annotators are a stack component that enables the use of data annotation as part
of your ZenML stack and pipelines. You can use the associated CLI command to
launch annotation, configure your datasets and get stats on how many labeled
tasks you have ready for use.

## Artifact

Artifacts are the data that power your experimentation and model training. It is
actually steps that produce artifacts, which are then stored in the artifact
store.

Artifacts can be serialized and deserialized (i.e. written and read from the
Artifact Store) in different ways like `TFRecord`s or saved model pickles,
depending on what the step produces. The serialization and deserialization logic
of artifacts is defined by Materializers.

## Artifact Store

An artifact store is a stack component which is responsible for the storage of 
artifacts. These artifacts may  have been produced by the pipeline steps, 
or they may be the data first ingested into a pipeline via an ingestion step.

## CLI

Our command-line tool is your entry point into ZenML. You install this tool and
use it to set up and configure your repository to work with ZenML. A single
`init` command serves to get you started, and then you can provision the
infrastructure that you wish to work with using the `stack register`
command with the relevant arguments passed in.

## Container Registry

A container registry in ZenML is a type of stack component tasked with storing 
(Docker) containers. A ZenML workflow involving a container registry would see 
you spinning up a Kubernetes cluster and then deploying a pipeline to be run on 
Kubeflow Pipelines. As part of the deployment to the cluster, the ZenML base 
image would be downloaded (from a cloud container registry) and used as the 
basis for the deployed 'run'. When you are running a local Kubeflow stack, you 
would therefore have a local container registry which stores the container 
images you create that bundle up your pipeline code. These images would in turn 
be built on top of a base image or custom image of your choice.

## DAG

Pipelines are traditionally represented as DAGs. DAG is an acronym for Directed
Acyclic Graph.

- Directed, because the nodes of the graph (i.e. the steps of a pipeline), have
  a sequence. Nodes do not exist as freestanding entities in this way.
- Acyclic, because there must be one (or more) straight paths through the graph
  from the beginning to the end. It is acyclic because the graph doesn't loop
  back on itself at any point.
- Graph, because the steps of the pipeline are represented as nodes in a graph.

ZenML follows this paradigm, and it is a useful mental model to have in your 
head when thinking about how the pieces of your pipeline get executed and how
dependencies between the different stages are managed.

## Data Validator

Data Validators are stack components which can help you to ensure and maintain
data quality not only in the initial stages of model development, but 
throughout the entire machine learning project lifecycle.

## Experiment Tracker

Experiment trackers are stack components which let you track your ML 
experiments by logging extended information about your models, datasets, 
metrics and other parameters and allowing you to browse them, visualize them 
and compare them between runs.

## Feature Store

In ZenML, a feature store as a stack component allows data teams to serve 
data via an offline store and an online low-latency store where data is kept 
in sync between the two. It also offers a centralized registry where 
features (and feature schemas) are stored for use within a team or wider 
organization.

## Integrations

An integration is a third-party tool or platform that implements a ZenML 
abstraction. A tool can implement many abstractions and therefore an 
integration can have different entrypoints for the user. We have a consistently 
updated integrations page which shows all current integrations supported by the 
ZenML core team [here](../component-gallery/integrations.md). However, as ZenML 
is a framework users are encouraged to use these as a guideline and implement 
their own integrations by extending the various ZenML abstractions.

## Materializers

A materializer defines how and where Artifacts live in between steps. It is used
to convert a ZenML artifact into a specific format. They are most often used to
handle the input or output of ZenML steps, and can be extended by building on
the `BaseMaterializer` class. We care about this because steps are not just
isolated pieces of work; they are linked together and the outputs of one-step
might well be the inputs of the next.

We have some built-in ways to serialize and deserialize the data flowing between
steps. Of course, if you are using some library or tool which doesn't work with
our built-in options, you can write
[your own custom materializer](../advanced-guide/pipelines/materializers.md)
to ensure that your data can be passed from step to step in this way. We use our
[`fileio` utilities](https://apidocs.zenml.io/latest/core_code_docs/core-io/)
to do the disk operations without needing to be concerned with whether we're
operating on a local or cloud machine.

## Model Deployer

Model deployers are stack components responsible for serving models on a 
real-time or batch basis.

## Orchestrator

An orchestrator manages the running of each step of the pipeline, administering
the actual pipeline runs. You can think of it as the 'root' of any pipeline job
that you run during your experimentation.

## Parameter

When we think about steps as functions, we know they receive input in the form
of artifacts. We also know that they produce output (also in the form of
artifacts, stored in the artifact store). But steps also take parameters. The
parameters that you pass into the steps are also (helpfully!) stored by ZenML. 
This helps freeze the iterations of your experimentation workflow in time, so
you can return to them exactly as you ran them.

## Pipeline

Pipelines are designed as basic Python functions. They are created by using 
decorators appropriate to the specific use case you have. The moment it is 
`run`, a pipeline is compiled and passed directly to the orchestrator, to be 
run in the orchestrator environment.

Within your repository, you will have one or more pipelines as part of your
experimentation workflow. A ZenML pipeline is a sequence of tasks that execute
in a specific order and yield artifacts. The artifacts are stored within the
artifact store and indexed via the ZenML Server. Each individual task within a
pipeline is known as a step.

## Repository

Every ZenML project starts inside a ZenML repository and, it is at the core of
all ZenML activity. Every action that can be executed within ZenML must take
place within such a repository. ZenML repositories are denoted by a local `.zen`
folder in your project root where various information about your local
configuration lives, e.g., the active [Stack](../starter-guide/stacks/stacks.md) 
that you are using to run pipelines, is stored.

## Runner Scripts

A runner script is a Python file, usually called `run.py` and located at the 
root of a ZenML repository, which has the code to actually create a pipeline 
run. The code usually looks like this:

```python
from pipelines.my_pipeline import my_pipeline
from steps.step_1 import step_1

if __name__ == "__main__":
    p = my_pipeline(
        step_1=step_1(),
    )
    p.run()
```

## Secret

A ZenML Secret is a grouping of key-value pairs. These are accessed and
administered via the ZenML Secret Manager (a stack component).

Secrets are distinguished by having different schemas. An AWS SecretSchema, for
example, has key-value pairs for `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`
as well as an optional `AWS_SESSION_TOKEN`. If you don't specify a schema at the
point of registration, ZenML will set the schema as `ArbitrarySecretSchema`, a
kind of default schema where things that aren't attached to a grouping can be
stored.

## Secrets Manager

Secrets managers as stack components provide a secure way of storing 
confidential information that is needed to run your ML pipelines. Most 
production pipelines will run on cloud infrastructure and therefore need 
credentials to authenticate with those services. Instead of storing these 
credentials in code or files, ZenML secrets managers can be used to store and 
retrieve these values in a secure manner.

## Stack

In ZenML, a **Stack** represents a set of configurations for your MLOps tools
and infrastructure. It is made up of various stack components, two of which are 
required in each stack:

- An Artifact Store
- An Orchestrator


## Step

A step is a single piece or stage of a ZenML pipeline. Think of each step as
being one of the nodes of the DAG. Steps are responsible for one aspect of
processing or interacting with the data / artifacts in the pipeline.

## Step Operator

The step operator as a stack component enables the execution of individual 
pipeline steps in specialized runtime environments that are optimized for 
certain workloads. These specialized environments can give your steps access 
to resources like GPUs or distributed processing frameworks like Spark.

## Source root

The source root refers to the root directory of your source files when running a pipeline.
ZenML will try to determine the source root in the following order:
* If you've created a [ZenML repository](../starter-guide/stacks/stacks.md) for your project,
the repository directory will be used.
* Otherwise, the parent directory of the Python file you're executing will be the source root.
For example, running `python /path/to/file.py`, the source root would be `/path/to`.
