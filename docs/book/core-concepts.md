---
description: A good place to start before diving further into the docs.
---

# Core Concepts

**ZenML** consists of the following key components:

![ZenML Architectural Overview](.gitbook/assets/architecture-overview-zenml.png)

## Repository

A **repository** is the foundation of all **ZenML** activity. Every action that can be executed within **ZenML** has to necessarily take place within a **ZenML repository**. **ZenML repositories** are inextricably tied to git.

<!-- ## Datasources

**Datasources** are the heart of any machine learning process and that's why they are first-class citizens in **ZenML**. While every **pipeline** takes one as input, a **datasource** can also be created independently of a **pipeline**. At that moment, an immutable snapshot of the data is created, versioned, and tracked in the **artifact store** and **metadata store** respectively. -->

## Pipelines

An **ZenML pipeline** is a sequence of steps that execute in a specific order and yield artifacts. The artifacts are stored within the **artifact store** and indexed via the **metadata store** \(see below\). The standard **pipelines** \(like `TrainingPipeline`\) within **ZenML** are designed to have easy interfaces to add pre-decided **steps**, with the order also pre-decided. Other sorts of **pipelines** can be created as well from scratch.

<!-- The moment a pipeline is executed with `run()`, a **pipeline** is converted to an immutable, declarative YAML configuration file, stored in the **pipelines directory** \(see below\). These YAML files may be persisted within the git repository as well or kept separate. -->

## Steps

A **step** is one part of a **ZenML pipeline**. It is a representation of a single task responsible for one aspect of processing the data. **Steps** can be thought of as hierarchical: there are step types (e.g. `SplitStep`, `PreprocessorStep`, and `TrainerStep`), which define interfaces for specialized implementations of these concepts.

<!-- TODO: add something about which of these step types we have right now (i.e. only SimpleStep and BaseStep?) -->

As an example, let's look at the `TrainerStep`. Here is the hierarchy:

```text
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

Each layer defines its own special interface that is essentially placeholder functions that can be overridden. If you wish to create a custom trainer **step**, you should subclass the appropriate class based on your specific requirements.

<!-- TODO: Consider revisiting 'backend' as a term (and maybe reinstate this paragraph?) -->
<!-- ## Backends

If **datasources** represent the data you use, and **pipelines** and **steps** define the code you use, **backends** define the configuration and environment with which everything comes together. **Backends** give the freedom to separate infrastructure from code, which is so crucial in production environments. They define where and how the code runs.

**Backends** are defined either per **pipeline** \(here they are called `OrchestratorBackends`\), or per **step** \(i.e. `ProcessingBackends`, `TrainingBackends`\). -->

<!-- ## Pipelines Directory

A **pipelines directory** is where all the declarative configurations of all pipelines run within a **ZenML repository** are stored. These declarative configurations are the source of truth for everyone working in the repository and therefore serve as a database to track not only **pipelines** but **steps**, **datasources**, and **backends**, including all configurations. -->

## Artifact Store

**Pipelines** have **steps** that can ingest or produce **artifacts**. These artifacts are stored in the **artifact store**. Artifacts themselves can be of many types, for example such as [TFRecords](https://www.tensorflow.org/tutorials/load_data/tfrecord) or saved model pickles.

## Metadata Store

The configuration of each **pipeline**, **step**, and produced artifacts are all tracked within the **metadata store**. The **metadata store** is an SQL database, and can be `sqlite` or `mysql`.

# Important considerations

**Artifact stores** and **metadata stores** can be configured per **repository** as well as per **pipeline**. However, only **pipelines** with the same **artifact store** and **metadata store** are comparable, and therefore should not change to maintain the benefits of caching and consistency across **pipeline** runs.

<!-- TODO: NOTE THE USE OF 'stack' here; check what we use -->

On a high level, when data is read from an **artifact** the results are persisted in your **artifact store**. An orchestrator reads the data from the **artifact store** and begins preprocessing - either itself or alternatively on a dedicated processing **backend** like [Google Dataflow](https://cloud.google.com/dataflow). Every **pipeline step** reads its predecessor's result artifacts from the **artifact store** and writes its own result artifacts to the **artifact store**. Once preprocessing is done, the orchestration begins the training of your model - again either itself or on a separate / dedicated **training stack**. The trained model will be persisted in the **artifact store**, and optionally passed on to a **serving stack**.

A few rules apply:

<!-- TODO: check this whole document for the use of 'stack' which I used fairly liberally -->

- Every **orchestration backend** \(local, Google Cloud VMs, etc\) can run all **pipeline steps**, including training.
- **Orchestration stacks** have a selection of compatible **processing stacks**.
- **Pipelines** can be configured to utilize more powerful **processing** \(e.g. distributed\) and **training** \(e.g. Google AI Platform\) **backends**.

A quick example for large datasets makes this clearer. By default, your experiments will run locally. Pipelines that load large datasets would be severely bottlenecked, so you can configure [Google Dataflow](https://cloud.google.com/dataflow) as a **processing backend** for distributed computation, and [Google AI Platform](https://cloud.google.com/ai-platform) as a **training backend**.

## System design

The design choices in **ZenML** follow the understanding that production-ready model training **pipelines** need to be immutable, repeatable, discoverable, descriptive, and efficient. **ZenML** takes care of the orchestration of your **pipelines**, from sourcing data all the way to continuous training - no matter if it's running somewhere locally, in an on-premise data center, or in the cloud.

In different words, **ZenML** runs your **ML** code while taking care of the "**Op**eration**s**" for you. It takes care of:

- Interfacing between the individual processing **steps** \(splitting, transform, training\).
- Tracking of intermediate results and metadata
- Caching your processing artifacts.
- Parallelization of computing tasks.
- Ensuring the immutability of your pipelines from data sourcing to model artifacts.
- No matter where - cloud, on-prem, or locally.

<!-- TODO: reconsider this paragraph and the .md file it links to -->

Since production scenarios often look complex, **ZenML** is built with integrations in mind. **ZenML** supports an ever-growing [range of integrations](https://github.com/zenml-io/zenml/tree/9c7429befb9a99f21f92d13deee005306bd06d66/docs/book/getting-started/benefits/integrations.md) for processing, training, and serving, and you can always add custom integrations via our extensible interfaces.
