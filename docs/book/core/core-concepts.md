---
description: A good place to start before diving further into the docs.
---

# Core Concepts

## Core Concepts

**ZenML** consists of the following key components:

![ZenML Architectural Overview](<../.gitbook/assets/architecture_diagram (1) (2) (1).png>)

[**CLI**](../support/cli-command-reference.md)

Our command-line tool is your entry point into ZenML. You install this tool and use it to setup and configure your repository to work with ZenML. A simple `init` command serves to get you started, and then you can provision the infrastructure that you wish to work with easily using a simple `stack register` command with the relevant arguments passed in.

[**Repository**](repository.md)

A repository is at the core of all ZenML activity. Every action that can be executed within ZenML must take place within a ZenML repository. ZenML repositories are inextricably tied to `git`. ZenML creates a `.zen` folder at the root of your repository to manage your assets and metadata.

[**Pipeline**](pipelines.md)

Within your repository, you will have one or more pipelines as part of your experimentation workflow. A ZenML pipeline is a sequence of tasks that execute in a specific order and yield artifacts. The artifacts are stored within the artifact store and indexed via the metadata store. Each individual task within a pipeline is known as a step. The standard pipelines within ZenML are designed to have easy interfaces to add pre-decided steps, with the order also pre-decided. Other sorts of pipelines can be created as well from scratch.

Pipelines can be written as simple functions. They are created by using decorators appropriate to the specific use case you have. The moment it is `run`, a pipeline is compiled and passed directly to the orchestrator.

[**Step**](steps.md)

A step is a single piece or stage of a ZenML pipeline. Think of each step as being one of the nodes of the DAG. Steps are responsible for one aspect of processing or interacting with the data / artifacts in the pipeline. ZenML currently implements a basic `step` interface, but there will be other more customized interfaces (layered in a hierarchy) for specialized implementations. For example, broad steps like `@trainer`, `@split` and and so on.

[**Artifact Store**](stacks.md#artifact-stores)

An artifact store is a place where artifacts are stored. These artifacts may have been produced by the pipeline steps, or they may be the data first ingested into a pipeline via an ingestion step.

[**Artifact**](artifacts.md)

Artifacts are the data that power your experimentation and model training. It is actually steps that produce artifacts, which are then stored in the artifact store. Artifacts are written in the signature of a step like so:

```python
// Some code
def my_step(first_artifact: int, second_artifact: torch.nn.Module -> int:
    # first_artifact is an integer
    # second_artifact is a torch.nn.Module
    return 1
```

Artifacts can be serialized and deserialized (i.e. written and read from the Artifact Store) in many different ways like `TFRecord`s or saved model pickles, depending on what the step produces.The serialization and deserialization logic of artifacts is defined by  [materializers.md](../api-reference/zenml/materializers.md "mention").

****[**Materializers**](../api-reference/zenml/materializers.md)****

A materializer defines how and where Artifacts live in between steps.

[**Parameter**](steps.md#step-input-and-output)

When we think about steps as functions, we know they receive input in the form of artifacts. We also know that they produce output (also in the form of artifacts, stored in the artifact store). But steps also take parameters. The parameters that you pass into the steps are also (helpfully!) stored in the metadata store. This helps freeze the iterations of your experimentation workflow in time so you can return to them exactly as you ran them. Parameters can be passed in as a subclass of `BaseStepConfig` like so:

```python
from zenml.steps.base_step_config import BaseStepConfig

class MyStepConfig(BaseStepConfig):
    basic_param_1: int = 1
    basic_param_2: str = 2
    
@step
def my_step(params: MyStepConfig):
    # user params here
    pass
```

[**Metadata Store**](stacks.md#metadata-stores)

The configuration of each pipeline, step, backend, and produced artifacts are all tracked within the metadata store. The metadata store is an SQL database, and can be `sqlite` or `mysql`.

[**Metadata**](stacks.md#metadata-stores)

Metadata are the pieces of information tracked about the pipelines, experiments and configurations that you are are running with ZenML. Metadata are stored inside the metadata store.

[**Orchestrator**](stacks.md#orchestrator)

An orchestrator is a special kind of backend that manages the running of each step of the pipeline. Orchestrators administer the actual pipeline runs. You can think of it as the 'root' of any pipeline job that you run during your experimentation.

[**Stack**](stacks.md)

A stack is made up of the following three core components:

* An Artifact Store
* A Metadata Store
* An Orchestrator (backend)

A ZenML stack also happens to be a Pydantic `BaseSettings` class, which means that there are multiple ways to set it (via env variables or config files).

**Backend (Executors)**

Backends are the infrastructure and environments on which your steps run. There are different kinds of backends depending on the particular use case. COMING SOON

**Tying Things All Together**

ZenML's core abstractions are either close to or replicate completely the commonly-found abstractions found in the industry for pipeline-style workflows. As a data scientist, it perhaps isn't natural to think of your work from within this 'pipeline' abstraction, but we think you'll see the benefits if you try it out with some examples. Check out our Get Started guide to see an example of what ZenML will add to your current workflow!

## Important considerations

**Artifact stores** and **metadata stores** can be configured per **repository** as well as per **pipeline**. However, only **pipelines** with the same **artifact store** and **metadata store** are comparable, and therefore should not change to maintain the benefits of caching and consistency across **pipeline** runs.

On a high level, when data is read from an **artifact** the results are persisted in your **artifact store**. An orchestrator reads the data from the **artifact store** and begins preprocessing - either itself or alternatively on a dedicated processing **backend** like [Google Dataflow](https://cloud.google.com/dataflow). Every **pipeline step** reads its predecessor's result artifacts from the **artifact store** and writes its own result artifacts to the **artifact store**. Once preprocessing is done, the orchestration begins the training of your model - again either itself or on a separate / dedicated **training backend**. The trained model will be persisted in the **artifact store**, and optionally passed on to a **serving backend**.

A few rules apply:

* Every **orchestrator** (local, Google Cloud VMs, etc) can run all **pipeline steps**, including training.
* **Orchestrators** have a selection of compatible **processing backends**.
* **Pipelines** can be configured to utilize more powerful **processing** (e.g. distributed) and **training** (e.g. Google AI Platform) **executors**.

A quick example for large datasets makes this clearer. By default, your experiments will run locally. Pipelines that load large datasets would be severely bottlenecked, so you can configure [Google Dataflow](https://cloud.google.com/dataflow) as a **processing executor** for distributed computation, and [Google AI Platform](https://cloud.google.com/ai-platform) as a **training executor**.

### System design

The design choices in **ZenML** follow the understanding that production-ready model training **pipelines** need to be immutable, repeatable, discoverable, descriptive, and efficient. **ZenML** takes care of the orchestration of your **pipelines**, from sourcing data all the way to continuous training - no matter if it's running somewhere locally, in an on-premise data center, or in the cloud.

In different words, **ZenML** runs your **ML** code while taking care of the "**Op**eration**s**" for you. It takes care of:

* Interfacing between the individual processing **steps** (splitting, transform, training).
* Tracking of intermediate results and metadata
* Caching your processing artifacts.
* Parallelization of computing tasks.
* Ensuring the immutability of your pipelines from data sourcing to model artifacts.
* No matter where - cloud, on-prem, or locally.

Since production scenarios often look complex, **ZenML** is built with integrations in mind. **ZenML** will support a range of integrations for processing, training, and serving, and you can always add custom integrations via our extensible interfaces.
