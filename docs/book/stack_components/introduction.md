---
description: Setting up your MLOps infrastructure
---

Machine Learning in production is not just about designing and training models. 
It is a fractured space consisting of a wide variety of tasks ranging from 
experiment tracking to orchestration, from model deployment to monitoring, 
from drift detection to feature stores and much, much more than that. Even 
though there are already some seemingly well-established solutions for some 
of these tasks, it can become increasingly difficult to establish a running 
production system in a reliable and modular manner, once all these solutions 
are brought together.

For instance, this is a problem which occurs quite often in the case of the 
switch from a research setting to a production setting. Due to the lack of 
standards, the time and resources invested in a small PoC-like project can 
completely to waste, if the initial system can not be transferred to a 
production-grade setting.

At ZenML, we believe that this is one of the most important and challenging 
problems in the field of MLOps, and it can be solved with a set of 
well-structured abstractions. Owing to the nature of MLOps, it is critical 
that these abstractions do not only cover concepts such as pipelines, steps and 
materializers that we covered in the starter guide but also the infrastructure 
elements that the pipelines are running on. 

With that in mind, we will go through the three main concepts that our solution 
is based on: Stacks, Stack Components and Flavors.

## Stacks

The first concept that we will look into is the Stack. In ZenML, a Stack 
represents essentially a collection of all the configuration for the 
infrastructure of your MLOps platform. (TODO: One more motivational sentence)

Structurally, each Stack consists of different Stack Components of varying types. 
In the table below, you can find a short list of all the stack component types 
that you can use within your stack:

### List of different types of components

| Type of Stack Component | Required | Description                                                       |
|-------------------------|----------|-------------------------------------------------------------------|
| Orchestrator            | ✅        | Orchestrating the runs of your pipeline                           |
| Artifact Store          | ✅        | Storage for the artifacts created by your pipelines               |
| Metadata Store          | ✅        | Tracking the execution of your pipelines/steps                    |
| Container Registry      |          | Store for your containers                                         |
| Secrets Manager         |          | Centralized location for the storage of your secrets              |
| Step Operator           |          | Execution of individual steps in specialized runtime environments |
| Model Deployer          |          | Services/platforms responsible for online model serving           |
| Feature Store           |          | Management of your data/features                                  |
| Experiment Tracker      |          | Tracking your ML experiments                                      |
| Alerter                 |          | Sending alerts through specified channels                         |

Establishing a stack requires you to define at least of an orchestrator, 
an artifact store and a metadata store. The rest of the stack components are 
optional, and you can use them as you see fit.

## Stack Components

A Stack Component represents the abstraction interface that is created for a 
specific task in your ML workflow.

For instance,
### Using `pydantic`

```python
pydantic example
```

```python
class StackComponent(BaseModel, ABC):
    """Abstract StackComponent class for all 
    components of a ZenML stack."""

    # Instance configuration
    name: str
    uuid: UUID = Field(default_factory=uuid4)

    # Class parameters
    TYPE: ClassVar[StackComponentType]
    FLAVOR: ClassVar[str]

    ...
```

Pydantic configuration

```python
class BaseArtifactStore(StackComponent):
    """Base class for all ZenML artifact stores.
    
    Attributes:
        path: The root path of the artifact store.
    """
    # Instance configuration
    path: str

    # Class parameters
    TYPE: ClassVar[StackComponentType] = StackComponentType.ARTIFACT_STORE
    FLAVOR: ClassVar[str]
    SUPPORTED_SCHEMES: ClassVar[Set[str]]

    ...
```

## Flavors

```python
class LocalArtifactStore(BaseArtifactStore):
    """Artifact Store for local artifacts."""

    # Class configuration
    FLAVOR: ClassVar[str] = "local"
    SUPPORTED_SCHEMES: ClassVar[Set[str]] = {""}

    ...
```

provision, deprovision

## CLI

#### zenml stack list
#### zenml stack register
#### zenml stack-component list
#### zenml stack-component register
#### zenml stack-component flavor list
#### zenml stack-component flavor register

## Configuration and usage

Configuration with instance parameters
Configuration with secrets
Configuration with runtime configs

## Create your own flavors

```bash
zenml artifact-store flavor list
```
```bash
Running without an active repository root.
Running with active profile: 'default' (global)
┏━━━━━━━━┯━━━━━━━━━━━━━┯━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ FLAVOR │ INTEGRATION │ READY-TO-USE │ SOURCE                                                        ┃
┠────────┼─────────────┼──────────────┼───────────────────────────────────────────────────────────────┨
┃ local  │ built-in    │ ✅           │ zenml.artifact_stores.local_artifact_store.LocalArtifactStore ┃
┃ azure  │ azure       │ ✅           │ zenml.integrations.azure.artifact_stores.AzureArtifactStore   ┃
┃  gcp   │ gcp         │ ✅           │ zenml.integrations.gcp.artifact_stores.GCSArtifactStore       ┃
┃   s3   │ s3          │ ✅           │ zenml.integrations.s3.artifact_stores.S3ArtifactStore         ┃
┗━━━━━━━━┷━━━━━━━━━━━━━┷━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```
The flag 'READY-TO-USE' indicates whether you can directly create/use/manage a 
stack component with that specific flavor. You can bring a flavor to a state 
where it is 'READY-TO-USE' in two different ways. If the flavor belongs to a 
ZenML integration, you can use `zenml integration install <name-of-the-integration>` 
and if it doesn't, you can make sure that you are using ZenML in an 
environment where ZenML can import the flavor through its source.

```bash
zenml artifact-store flavor register TODO
```

```bash
zenml artifact-store flavor list
```

