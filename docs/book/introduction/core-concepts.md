---
description: A good place to start before diving further into the docs.
---

# Core Concepts

**ZenML** consists of the following key components:

![ZenML Architectural Overview](../assets/architecture.png)

**Repository**

Every ZenML project starts inside a ZenML repository and, it is at the core of all ZenML activity. Every action that 
can be executed within ZenML must take place within such a repository. 

In order to create a ZenML repository, do the following after having installed ZenML:

```
zenml init
```

The initialization creates a local `.zen` folder where various information about your local configuration lives, 
e.g., the active [Stack](../guides/functional-api/deploy-to-production.md) that you are using to run pipelines.

**Pipeline**

Pipelines are designed as simple functions. They are created by using decorators appropriate to the specific use case 
you have. The moment it is `run`, a pipeline is compiled and passed directly to the orchestrator, to be run in the 
orchestrator environment.

Within your repository, you will have one or more pipelines as part of your experimentation workflow. A ZenML 
pipeline is a sequence of tasks that execute in a specific order and yield artifacts. The artifacts are stored 
within the artifact store and indexed via the metadata store. Each individual task within a pipeline is known as a 
step. The standard pipelines (like `TrainingPipeline`) within ZenML are designed to have easy interfaces to add 
pre-decided steps, with the order also pre-decided. Other sorts of pipelines can be created as well from scratch.

```python
@pipeline
def mnist_pipeline(
    importer,
    normalizer: normalizer,
    trainer,
    evaluator,
):
    # Link all the steps artifacts together
    X_train, y_train, X_test, y_test = importer()
    X_trained_normed, X_test_normed = normalizer(X_train=X_train, X_test=X_test)
    model = trainer(X_train=X_trained_normed, y_train=y_train)
    evaluator(X_test=X_test_normed, y_test=y_test, model=model)


# Initialize the pipeline
p = mnist_pipeline(
    importer=importer_mnist(),
    normalizer=normalizer(),
    trainer=trainer(config=TrainerConfig(epochs=1)),
    evaluator=evaluator(),
)

# Run the pipeline
p.run()
```

Pipelines consist of many steps that define what actually happens to the data flowing through 
the pipelines.

**Step**

A step is a single piece or stage of a ZenML pipeline. Think of each step as being one of the nodes of the DAG. 
Steps are responsible for one aspect of processing or interacting with the data / artifacts in the pipeline. ZenML 
currently implements a basic `step` interface, but there will be other more customized interfaces (layered in a 
hierarchy) for specialized implementations. For example, broad steps like `@trainer`, `@split` and so on. 
Conceptually, a `Step` is a discrete and independent part of a pipeline that is responsible for one particular aspect 
of data manipulation inside a ZenML pipeline.

A ZenML installation already comes with many `standard` steps found in `zenml.core.steps.*` for users to get 
started. For example, a `SplitStep` is responsible for splitting the data into various split's like `train` and 
`eval` for downstream steps to then use. However, in essence, virtually any Python function can be a ZenML step as well.

```python
from zenml.steps import step

@step  # this is where the magic happens
def simplest_step_ever(basic_param_1: int, basic_param_2: str) -> int:
    return basic_param_1 + int(basic_param_2)
```

There are only a few considerations for the parameters and return types.

* All parameters passed into the signature must be [typed](https://docs.python.org/3/library/typing.html). Similarly, 
if you're returning something, it must be also be typed with the return operator (`->`)
* ZenML uses [Pydantic](https://pydantic-docs.helpmanual.io/usage/types/) for type checking and serialization 
under-the-hood, so all [Pydantic types](https://pydantic-docs.helpmanual.io/usage/types/) are 
supported \[full list available soon].

While this is just a function with a decorator, it is not super useful. ZenML
steps really get powerful when you put them together with data artifacts. Read
about more of that
[here](https://docs.zenml.io/v/docs/guides/functional-api/materialize-artifacts)!

**Artifact Store**

An artifact store is a place where artifacts are stored. These artifacts may have been produced by the pipeline 
steps, or they may be the data first ingested into a pipeline via an ingestion step.

**Artifact**

Artifacts are the data that power your experimentation and model training. It is actually steps that produce 
artifacts, which are then stored in the artifact store. Artifacts are written in the signature of a step like so:

```python
// Some code
def my_step(first_artifact: int, second_artifact: torch.nn.Module -> int:
    # first_artifact is an integer
    # second_artifact is a torch.nn.Module
    return 1
```

Artifacts can be serialized and deserialized (i.e. written and read from the Artifact Store) in different ways 
like `TFRecord`s or saved model pickles, depending on what the step produces.The serialization and deserialization 
logic of artifacts is defined by Materializers.

**Materializers**

A materializer defines how and where Artifacts live in between steps. It is used to convert a ZenML artifact into 
a specific format. They are most often used to handle the input or output of ZenML steps, and can be extended by 
building on the `BaseMaterializer` class. We care about this because steps are not just isolated pieces of work; 
they are linked together and the outputs of one step might well be the inputs of the next.

We have some built-in ways to serialize and deserialize the data flowing between steps. Of course, if you are 
using some library or tool which doesn't work with our built-in options, you can write 
[your own custom materializer](https://docs.zenml.io/guides/functional-api/materialize-artifacts) to ensure that your data can 
be passed from step to step in this way. We use our 
[`fileio` utilities](https://apidocs.zenml.io/api_reference/zenml.io.fileio.html) to do the disk operations 
without needing to be concerned with whether we're operating on a local or cloud machine.

**Parameter**

When we think about steps as functions, we know they receive input in the form of artifacts. We also know that 
they produce output (also in the form of artifacts, stored in the artifact store). But steps also take parameters. 
The parameters that you pass into the steps are also (helpfully!) stored in the metadata store. This helps freeze the 
iterations of your experimentation workflow in time, so you can return to them exactly as you ran them. Parameters can 
be passed in as a subclass of `BaseStepConfig` like so:

```python
from zenml.steps import BaseStepConfig

class MyStepConfig(BaseStepConfig):
    basic_param_1: int = 1
    basic_param_2: str = 2

@step
def my_step(params: MyStepConfig):
    # user params here
    pass
```

**Metadata Store**

The configuration of each pipeline, step and produced artifacts are all tracked within the metadata store. 
The metadata store is an SQL database, and can be `sqlite` or `mysql`.

**Metadata**

Metadata are the pieces of information tracked about the pipelines, experiments and configurations that you are running 
with ZenML. Metadata are stored inside the metadata store.

**Orchestrator**

An orchestrator manages the running of each step of the pipeline, administering the actual pipeline runs. You can 
think of it as the 'root' of any pipeline job that you run during your experimentation.

**Stack**

A stack is made up of the following three core components:

- An Artifact Store
- A Metadata Store
- An Orchestrator

A ZenML stack also happens to be a Pydantic `BaseSettings` class, which means that there are multiple ways to use it.

```bash
zenml stack register STACK_NAME \
    -m METADATA_STORE_NAME \
    -a ARTIFACT_STORE_NAME \
    -o ORCHESTRATOR_NAME
```

**Container Registry**

A container registry is a store for (Docker) containers. A ZenML workflow involving a container registry would see 
you spinning up a Kubernetes cluster and then deploying a pipeline to be run on Kubeflow Pipelines. As part of the 
deployment to the cluster, the ZenML base image would be downloaded (from a cloud container registry) and used as 
the basis for the deployed 'run'. When you are running a local Kubeflow stack, you would therefore have a local 
container registry which stores the container images you create that bundle up your pipeline code. These images 
would in turn be built on top of a base image or custom image of your choice.

**Visualizers**

Visualizers contain logic to create visualizations within the ZenML ecosystem.

**Tying Things All Together**

ZenML's core abstractions are either close to or replicate completely the commonly-found abstractions found in the 
industry for pipeline-style workflows. As a data scientist, it perhaps isn't natural to think of your work from 
within this 'pipeline' abstraction, but we think you'll see the benefits if you try it out with some examples. 
Check out our Get Started guide to see an example of what ZenML will add to your current workflow!

## Important considerations

**Artifact stores** and **metadata stores** can be configured per **repository** as well as per **pipeline**. 
However, only **pipelines** with the same **artifact store** and **metadata store** are comparable, and therefore 
should not change to maintain the benefits of caching and consistency across **pipeline** runs.

On a high level, when data is read from an **artifact** the results are persisted in your **artifact store**. 
An orchestrator reads the data from the **artifact store** and begins preprocessing - either itself or alternatively 
on dedicated cloud infrastructure like [Google Dataflow](https://cloud.google.com/dataflow). Every **pipeline step** 
reads its predecessor's result artifacts from the **artifact store** and writes its own result artifacts to the 
**artifact store**. Once preprocessing is done, the orchestration begins the training of your model - again either 
itself or on separate / dedicated **training infrastructure**. The trained model will be persisted in the 
**artifact store**, and optionally passed on to **serving infrastructure**.

A few rules apply:

- Every **orchestrator** (local, Google Cloud VMs, etc) can run all **pipeline steps**, including training.
- **Orchestrators** have a selection of compatible **processing infrastructure**.
- **Pipelines** can be configured to utilize more powerful **processing** (e.g. distributed) and **training** 
(e.g. Google AI Platform) **executors**.

A quick example for large datasets makes this clearer. By default, your experiments will run locally. Pipelines that 
load large datasets would be severely bottlenecked, so you can configure 
[Google Dataflow](https://cloud.google.com/dataflow) as a **processing executor** for distributed computation, 
and [Google AI Platform](https://cloud.google.com/ai-platform) as a **training executor**.

### System design

The design choices in **ZenML** follow the understanding that production-ready model training **pipelines** need 
to be immutable, repeatable, discoverable, descriptive, and efficient. **ZenML** takes care of the orchestration 
of your **pipelines**, from sourcing data all the way to continuous training - no matter if it's running somewhere 
locally, in an on-premise data center, or in the cloud.

In different words, **ZenML** runs your **ML** code while taking care of the "**Op**eration**s**" for you. It takes 
care of:

* Interfacing between the individual processing **steps** (splitting, transform, training).
* Tracking of intermediate results and metadata
* Caching your processing artifacts.
* Parallelization of computing tasks.
* Ensuring the immutability of your pipelines from data sourcing to model artifacts.
* No matter where - cloud, on-prem, or locally.

Since production scenarios often look complex, **ZenML** is built with integrations in mind. **ZenML** will support a 
range of integrations for processing, training, and serving, and you can always add custom integrations via our 
extensible interfaces.
