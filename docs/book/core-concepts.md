---
description: A good place to start before diving further into the docs.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To check the latest version please [visit https://docs.zenml.io](https://docs.zenml.io)
{% endhint %}


# Core Concepts

ZenML consists of a number of components. We mostly follow industry naming
conventions for the most part, so a lot should already be broadly
comprehensible. This guide walks through the various pieces you'll encounter
when using ZenML, starting with the most basic to things you'll only encounter
when deploying your work to the cloud. At the very highest level, the workflow
is as follows:

- You write your code as a pipeline to define what you want to happen in your machine learning
  workflow
- You configure a ZenML Stack which is the infrastructure and setup that will
  run your machine learning code.
- A stack consists of stack components that interact with your pipeline and its steps in various ways.
- You can easily switch between different Stacks (i.e. infrastructure
  configurations) depending on your needs at any given moment.
- You can use whatever you want as part of your Stacks as we're built as a
  framework to be extensible

Let's get back to basics, though, and dive into all the core concepts that
you'll come across when using ZenML!

## Basics: Steps and Pipelines

At its core, ZenML follows a pipeline-based workflow for your data projects.
Pipelines consist of a series of steps, organized in whatever order makes sense
for your particular use case.

![The most basic ZenML pipeline](assets/core_concepts/concepts-1.png)

Here you can see three steps, each running one after another. Your set of steps
might have dependencies between them, with one step using the output of a
previous step and thus waiting until it is able to start its work.

Pipelines and steps are defined in code using handy decorators to designate
functions as being one or the other. This is where the core business logic and
value of your work lives and you will spend most of your time defining these two
things. (Your code lives inside a Repository, which is the main abstraction
within which your project-specific pipelines should live.)

When it comes time to run your pipeline, ZenML offers an abstraction to handle
all the decisions around how your pipeline gets run. The different stack
components interact in different ways depending on how you've written your
pipeline.

## Stacks, Components and Stores

A Stack represents the infrastructure needed to run your pipeline as well as
some of the extra requirements needed for ML pipelines. ZenML comes with a
default stack that runs locally, as seen in the following diagram:

![ZenML pipelines run on stacks](assets/core_concepts/concepts-2.png)

A Stack is the configuration of the underlying infrastructure and choices around
how your pipeline will be run. There are three Stack Components which are
required in any stack:

- An Orchestrator

This is the workhorse that runs all the steps of your pipeline. Given that
pipelines can be set up with complex combinations of steps with various
asynchronous dependencies between them, a special component is needed to decide
what steps to run when, and how to pass data between the steps. ZenML comes with
a built-in local orchestrator but we also support more fully-featured options
like Airflow and Kubeflow.

- An Artifact Store

All the data that passes through your pipelines is stored in the Artifact Store.
These artifacts may have been produced by the pipeline steps, or they may be the
data first ingested into a pipeline via an ingestion step. An artifact store
will store all intermediary pipeline step results, which in turn will be tracked
in the metadata store. The fact that all your data inputs / outputs are tracked
and versioned here in the artifact store allows for extremely useful features
like data caching which speed up your pace of experimentation.

- A Metadata Store

A Metadata Store keeps track of all the bits of extraneous data regarding a
pipeline run. It allows you to fetch specific steps from your pipeline run and
their output artifacts in a post-execution workflow.

When you start working with ZenML, you'll likely spend most of your initial time
here at this stage, working with the default stack provided to you on
initialization. ZenML functions as a way of managing the pipeline workflows that
you define, data gets cached and you are able to access your previous
experiments through the metadata store.

At a certain point, however, you'll want to do something that requires a bit
more compute power - perhaps requiring GPUs for model training - or some custom
functionality at which point you'll want to add some extra components to your
stack. These stacks will supercharge your steps and pipelines with extra functionality 
which you can then use in production!

## Cloud Training, Deployment, Monitoring...

When you are ready to switch out your infrastructure and the components used as
part of your machine learning workflow, it's as simple as a four word CLI
command that switches out your stack. The code defining your steps and pipelines
stays the same, but it gets run in whatever cloud infrastructure you've set up
in your custom stack; all you change is the stack you're using and your pipeline
code gets run someplace different.

![Running your pipeline in the cloud](assets/core_concepts/concepts-3.png)

Running workflows in the cloud often requires certain custom behaviors, so ZenML
offers a number of extra Stack Components that handle these common use cases.
For example, it's common to want to deploy models so we have a Model Deployer
component. Similarly, you might want to use popular tools like Weights & Biases
or MLflow to track your experiments, so we have an Experiment Tracker stack
component. Any additional software needed for these components can be added and
installed by using ZenML's Integration installer.

It is this modular and configurable nature of the ZenML stack that offers you
ways to get productive quickly. If we don't support some specific tool you want
to use, our stack components are easily extensible so this shouldn't be a
barrier for you.

All the stack components configured as part of the stack carry their
configuration parameters so whether it's an AWS Sagemaker cluster you need to
run your training on or an Google Cloud container registry you need to connect
to, ZenML handles the connections between these various parts on your behalf.

## Bits and Pieces

There are lots of different ways to use ZenML which will depend on your precise
use case. The following concepts and stack components are things you'll possibly
encounter further down the road while using ZenML.

- **Materializers** - ZenML stores the data inputs and outputs to your steps in the
  Artifact Store as we saw above. In order to store the data, it needs to
  serialize everything in a format that can fit into the Artifact Store. ZenML
  handles serialization (and deserialization) of the most common artifacts, but
  if you try to do something we haven't already thought of you'll need to write
  your own custom materializer. This isn't hard, but you should be aware that
  it's something you might need do to. The ZenML CLI will let you know with a
  clear error message when you need to do this.
- **Profiles** - Profiles are groupings of stacks. You might want to keep all your
  AWS stacks separate from your GCP stacks, for example, or your work
  infrastructure use separate from that which you use for your personal
  projects. Profiles allow you to separate these out, and switching between them
  is easy.
- **Service** - A service is a longer-lived entity that extends the capabilities of
  ZenML beyond the run of a pipeline. For example, a service could be a
  prediction service that loads models for inference in a production setting.
- **ZenServer** - ZenML is building out functionality to host a shared server that
  allows teams to collaborate and share stacks, data stores and more.

There's a lot more detail to digest when it comes to ZenML, but with the above
you should be sufficiently armed to understand how the framework works and where
you might want to extend it.
