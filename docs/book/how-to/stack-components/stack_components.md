---
description: Understanding and working with ZenML Stacks and Stack Components
icon: cubes
---

# Stack & Components

## Understanding ZenML Stacks

A ZenML stack is a collection of components that together form an MLOps infrastructure to run your ML pipelines. While your pipeline code defines what happens in your ML workflow, the stack determines where and how that code runs.

### Why Stacks Matter

Stacks provide several key benefits:

1. **Environment Flexibility**: Run the same pipeline code locally during development and in the cloud for production
2. **Infrastructure Separation**: Change your infrastructure without modifying your pipeline code
3. **Specialized Resources**: Use specialized tools for different aspects of your ML workflow
4. **Team Collaboration**: Share infrastructure configurations across your team
5. **Reproducibility**: Ensure consistent pipeline execution across different environments

### Stacks for Environment Organization

Stacks provide a powerful way to organize your execution environments:

* **Development**: Use a local stack for rapid iteration and debugging
* **Staging**: Deploy a cloud stack with modest resources for integration testing
* **Production**: Use a production-grade stack with robust resources and security

This separation helps you:
* Control costs by using appropriate resources for each environment
* Prevent accidental deployments to production
* Manage access control by restricting who can use which stacks

### Stack Structure

Each ZenML stack must include these core components:

* **Orchestrator**: Controls how your pipeline steps are executed
* **Artifact Store**: Manages where your pipeline artifacts are stored

Stacks may also include these optional components:

* **Container Registry**: Stores Docker images for your pipeline steps
* **Step Operator**: Runs specific steps on specialized hardware
* **Model Deployer**: Deploys models as prediction services
* **Experiment Tracker**: Tracks metrics and parameters
* **Feature Store**: Manages ML features
* **Alerter**: Sends notifications about pipeline events
* **Annotator**: Manages data labeling workflows

### Stacks and Pipeline Execution

When you run a pipeline, ZenML:

1. Checks which stack is active
2. Uses the orchestrator from that stack to execute the pipeline steps
3. Stores artifacts in the artifact store from that stack
4. Utilizes any other configured components as needed

This abstraction allows you to focus on building your pipeline logic without worrying about the underlying infrastructure.

## Stack Components

Stack components are modular building blocks that provide specific functionality. Each component type comes in different flavors - implementations for specific tools or services.

### Core Components

#### Orchestrators

Orchestrators determine how your pipeline steps are executed:

* **Local**: Runs steps sequentially on your local machine (default)
* **Kubernetes**: Runs steps as Kubernetes jobs
* **Kubeflow**: Uses Kubeflow Pipelines
* **Vertex AI, AzureML, SageMaker**: Runs on managed cloud services

#### Artifact Stores

Artifact stores determine where pipeline artifacts are saved:

* **Local**: Stores artifacts on your local filesystem (default)
* **S3**: Uses Amazon S3 buckets
* **GCS**: Stores in Google Cloud Storage
* **Azure Blob**: Uses Azure Blob Storage

### Component Interactions

Components in a stack work together to support your ML pipeline:

1. The **orchestrator** executes your pipeline steps
2. Each step produces artifacts stored in the **artifact store**
3. The orchestrator may use the **container registry** for containerized execution
4. Specialized steps might use a **step operator** for execution
5. Models can be deployed via a **model deployer**
6. Metrics are tracked in an **experiment tracker**

## Working with Stacks

### The Active Stack

In ZenML, you always have an active stack that's used when you run a pipeline:

```bash
# See your active stack
zenml stack describe

# Switch to a different stack
zenml stack set STACK_NAME
```

### Managing Stacks

You can create and manage stacks through the CLI:

```bash
# List all stacks
zenml stack list

# Register a new stack with minimal components
zenml stack register my-stack -a local-store -o local-orchestrator

# Register a stack with additional components
zenml stack register production-stack \
    -a s3-store \
    -o kubeflow \
    --container-registry ecr-registry \
    --experiment-tracker mlflow-tracker
```

Or through the Python API:

```python
from zenml.client import Client

client = Client()
# List all stacks
stacks = client.list_stacks()

# Set active stack
client.activate_stack("my-stack")
```

### Local vs. Cloud Stacks

ZenML provides two main types of stacks:

1. **Local Stack**: Uses your local machine for orchestration and storage. This is the default and requires no additional setup.

2. **Cloud Stack**: Uses cloud services for orchestration, storage, and other components. These stacks offer more scalability and features but require additional deployment and configuration.

When you start with ZenML, you're automatically using a local stack. As your ML projects grow, you'll likely want to deploy cloud stacks to handle larger workloads and collaborate with your team.

## Next Steps

Now that you understand what stacks are, you might want to:

* Learn about [deploying stacks](deployment.md) on cloud platforms
* Understand [Service Connectors](service_connectors.md) for authenticating with cloud services
* Explore how to [register existing cloud resources](https://docs.zenml.io/how-to/infrastructure-deployment/stack-deployment/register-a-cloud-stack) as ZenML stack components
