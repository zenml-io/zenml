---
description: Understanding and working with ZenML Stacks and Stack Components
icon: cubes
---

# Stack & Components

## Understanding ZenML Stacks

A ZenML stack is a collection of components that together form an MLOps infrastructure to run your ML pipelines. Stacks allow you to seamlessly transition from local development to production environments without changing your pipeline code.

Each stack must include at least one:

* **Orchestrator**: The component that executes your pipeline steps
* **Artifact Store**: The component that stores and versions your pipeline artifacts

Additionally, stacks may include optional components such as:

* **Container Registry**: To store Docker images for your pipeline steps
* **Step Operator**: To run specific steps on specialized infrastructure
* **Model Deployer**: To deploy models as prediction services
* **Experiment Tracker**: To track metrics and parameters
* **Feature Store**: To manage and serve ML features
* **Alerter**: To notify you about pipeline events
* **Annotator**: To manage data labeling workflows

## Stack Components

Stack components are modular building blocks that provide specific functionality to your MLOps infrastructure. Each component type comes in different flavors, which are implementations of the component interface for specific tools or services.

### Core Component Types

#### Orchestrators

Orchestrators are responsible for executing pipeline steps according to their dependencies. They determine where and how your code runs. Examples include:

* **Local**: Runs steps sequentially on your local machine
* **Kubernetes**: Orchestrates steps as Kubernetes jobs
* **Kubeflow**: Uses Kubeflow Pipelines to run steps
* **Vertex**: Runs pipelines on Google Cloud Vertex AI
* **AzureML**: Executes pipelines on Azure Machine Learning

#### Artifact Stores

Artifact stores manage the data produced and consumed by pipeline steps. They handle storage, versioning, and retrieval of artifacts. Examples include:

* **Local**: Stores artifacts on your local filesystem
* **S3**: Uses Amazon S3 buckets for artifacts
* **GCS**: Stores artifacts in Google Cloud Storage
* **Azure Blob**: Uses Azure Blob Storage for artifacts

#### Container Registries

Container registries store Docker images that encapsulate the environment for your pipeline steps. They ensure reproducibility and portability. Examples include:

* **Docker Hub**: The public Docker registry
* **ECR**: Amazon Elastic Container Registry
* **GCR**: Google Container Registry
* **ACR**: Azure Container Registry

## Working with Stacks

### Active Stack

In ZenML, you always have an active stack that is used when you run a pipeline. You can view your active stack with:

```bash
zenml stack describe
```

To switch to a different stack:

```bash
zenml stack set STACK_NAME
```

### Stack Management

You can manage your stacks through the ZenML CLI or the Python API:

```bash
# List all registered stacks
zenml stack list

# Get details about a specific stack
zenml stack describe STACK_NAME

# Register a new stack
zenml stack register STACK_NAME \
    -a ARTIFACT_STORE \
    -o ORCHESTRATOR \
    [optional components...]
```

Using the Python API:

```python
from zenml.client import Client

client = Client()
stacks = client.list_stacks()

# Set active stack
client.activate_stack("STACK_NAME")
```

## Using Service Connectors with Stack Components

Service connectors provide a unified way to handle authentication between ZenML and cloud services. They:

1. Simplify credential management
2. Support multiple authentication methods
3. Enable secure sharing of credentials among team members
4. Provide fine-grained access control to resources

Service connectors can be attached to stack components to authenticate with the underlying services, making it easier to work with different environments and cloud providers.

## Next Steps

* Learn about [Service Connectors](service_connectors.md) for authenticating with cloud providers
* Understand how to [deploy stacks](deployment.md) on cloud platforms
* Explore specific cloud providers: [AWS](aws.md), [Azure](azure.md), [GCP](gcp.md)
