# Glossary

## Artifact

Artifacts are the data that power your experimentation and model training. It is
actually steps that produce artifacts, which are then stored in the artifact
store.

Artifacts can be serialized and deserialized (i.e. written and read from the
Artifact Store) in different ways like `TFRecord`s or saved model pickles,
depending on what the step produces.The serialization and deserialization logic
of artifacts is defined by Materializers.

## Artifact Store

An artifact store is a place where artifacts are stored. These artifacts may
have been produced by the pipeline steps, or they may be the data first ingested
into a pipeline via an ingestion step.

## CLI

Our command-line tool is your entry point into ZenML. You install this tool and
use it to set up and configure your repository to work with ZenML. A simple
`init` command serves to get you started, and then you can provision the
infrastructure that you wish to work with easily using a simple `stack register`
command with the relevant arguments passed in.

## Container Registry

A container registry is a store for (Docker) containers. A ZenML workflow
involving a container registry would see you spinning up a Kubernetes cluster
and then deploying a pipeline to be run on Kubeflow Pipelines. As part of the
deployment to the cluster, the ZenML base image would be downloaded (from a
cloud container registry) and used as the basis for the deployed 'run'. When you
are running a local Kubeflow stack, you would therefore have a local container
registry which stores the container images you create that bundle up your
pipeline code. These images would in turn be built on top of a base image or
custom image of your choice.

## DAG

Pipelines are traditionally represented as DAGs. DAG is an acronym for Directed
Acyclic Graph.

- Directed, because the nodes of the graph (i.e. the steps of a pipeline), have
  a sequence. Nodes do not exist as free-standing entities in this way.
- Acyclic, because there must be one (or more) straight paths through the graph
  from the beginning to the end. It is acyclic because the graph doesn't loop
  back on itself at any point.
- Graph, because the steps of the pipeline are represented as nodes in a graph.

ZenML follows this paradigm and it is a useful mental model to have in your head
when thinking about how the pieces of your pipeline get executed and how
dependencies between the different stages are managed.

## Integrations

An integration is a third-party tool or platform that implements a ZenML abstraction. 
A tool can implement many abstractions and therefore an integration can have different 
entrypoints for the user. We have a consistently updated integrations page which shows all 
current integrations supported by the ZenML core team [here](../features/integrations.md). 
However, as ZenML is a framework users are encouraged to use these as a guideline and implement 
their own integrations by extending the various ZenML abstractions.

## Materializers

A materializer defines how and where Artifacts live in between steps. It is used
to convert a ZenML artifact into a specific format. They are most often used to
handle the input or output of ZenML steps, and can be extended by building on
the `BaseMaterializer` class. We care about this because steps are not just
isolated pieces of work; they are linked together and the outputs of one step
might well be the inputs of the next.

We have some built-in ways to serialize and deserialize the data flowing between
steps. Of course, if you are using some library or tool which doesn't work with
our built-in options, you can write
[your own custom materializer](https://docs.zenml.io/guides/functional-api/materialize-artifacts)
to ensure that your data can be passed from step to step in this way. We use our
[`fileio` utilities](https://apidocs.zenml.io/api_reference/zenml.io.fileio.html)
to do the disk operations without needing to be concerned with whether we're
operating on a local or cloud machine.

## Metadata

Metadata are the pieces of information tracked about the pipelines, experiments
and configurations that you are running with ZenML. Metadata are stored inside
the metadata store.

## Metadata Store

The configuration of each pipeline, step and produced artifacts are all tracked
within the metadata store. The metadata store is an SQL database, and can be
`sqlite` or `mysql`.

## Orchestrator

An orchestrator manages the running of each step of the pipeline, administering
the actual pipeline runs. You can think of it as the 'root' of any pipeline job
that you run during your experimentation.

## Parameter

When we think about steps as functions, we know they receive input in the form
of artifacts. We also know that they produce output (also in the form of
artifacts, stored in the artifact store). But steps also take parameters. The
parameters that you pass into the steps are also (helpfully!) stored in the
metadata store. This helps freeze the iterations of your experimentation
workflow in time, so you can return to them exactly as you ran them.

## Pipeline

Pipelines are designed as simple functions. They are created by using decorators
appropriate to the specific use case you have. The moment it is `run`, a
pipeline is compiled and passed directly to the orchestrator, to be run in the
orchestrator environment.

Within your repository, you will have one or more pipelines as part of your
experimentation workflow. A ZenML pipeline is a sequence of tasks that execute
in a specific order and yield artifacts. The artifacts are stored within the
artifact store and indexed via the metadata store. Each individual task within a
pipeline is known as a step.

## Repository

Every ZenML project starts inside a ZenML repository and, it is at the core of
all ZenML activity. Every action that can be executed within ZenML must take
place within such a repository. ZenML repositories are denoted by a local `.zen`
folder in your project root where various information about your local
configuration lives, e.g., the active
[Stack](../guides/functional-api/deploy-to-production.md) that you are using to
run pipelines, is stored.

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

Most projects involving either cloud infrastructure or of a certain complexity
will involve secrets of some kind. You use secrets, for example, when connecting
to AWS, which requires an `access_key_id` and a `secret_access_key` which it
(usually) stores in your `~/.aws/credentials` file.

You might find you need to access those secrets from within your Kubernetes
cluster as it runs individual steps, or you might just want a centralized
location for the storage of secrets across your project. ZenML offers a local
secrets manager and an integration with the managed [AWS Secrets
Manager](https://aws.amazon.com/secrets-manager).

## Stack

A stack is made up of the following three core components:

- An Artifact Store
- A Metadata Store
- An Orchestrator

A ZenML stack also happens to be a Pydantic `BaseSettings` class, which means
that there are multiple ways to use it.

```bash
zenml stack register STACK_NAME \
    -m METADATA_STORE_NAME \
    -a ARTIFACT_STORE_NAME \
    -o ORCHESTRATOR_NAME
```

## Step

A step is a single piece or stage of a ZenML pipeline. Think of each step as
being one of the nodes of the DAG. Steps are responsible for one aspect of
processing or interacting with the data / artifacts in the pipeline.

## Visualizer

A visualizer contains logic to create visualizations within the ZenML ecosystem.
