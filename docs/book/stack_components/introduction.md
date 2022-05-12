---
description: Setting up your MLOps infrastructure
---

Talking about the fractured space of MLOps and tooling

Different components of a production grade ML workflow

Moving from research to production

ZenML helps you with the concept of stacks and their extendable nature

## Abstractions

The base abstractions of ZenML.

Short description of what stacks, stack components and flavors mean

The aim of this document...

### Stack

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


