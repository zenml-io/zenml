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

As an example, this is a problem which occurs quite often in the case of the 
switch from a research setting to a production setting. Due to the lack of 
standards, the time and resources invested in a small PoC-like project can 
completely to waste, if the initial system can not be transferred to a 
production-grade setting.

At ZenML, we believe that this is one of the most important and challenging 
problems in the field of MLOps, and it can be solved with a set of 
well-structured abstractions. Owing to the nature of MLOps, it is critical 
that these abstractions do not only cover concepts such as pipelines, steps and 
materializer but also cover the infrastructure that these concepts are 
running on.

### Stack

In ZenML, this is where the concept of stacks comes into play. It 

The base abstractions of ZenML.

Short description of what stacks, stack components and flavors mean

The aim of this document...


#### List of components

| Type of Stack Component | Required | Description |
|-------------------------|----------|-------------|
| Orchestrator            | ✅        |             |
| Artifact Store          | ✅        |             |
| Metadata Store          | ✅        |             |
| Container Registry      |          |             |
| Secrets Manager         |          |             |
| Step Operator           |          |             |
| Model Deployer          |          |             |
| Feature Store           |          |             |
| Experiment Tracker      |          |             |
| Alerter                 |          |             |


### Stack Component

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

### Flavors

```python
class LocalArtifactStore(BaseArtifactStore):
    """Artifact Store for local artifacts."""

    # Class configuration
    FLAVOR: ClassVar[str] = "local"
    SUPPORTED_SCHEMES: ClassVar[Set[str]] = {""}

    ...
```

## Customize your ZenML

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

## Configuration and usage

Configuration with instance parameters
Configuration with secrets
Configuration with runtime configs


