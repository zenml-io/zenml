---
description: Understanding and working with ZenML Stacks and Stack Components
icon: cubes
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Stack & Components

A [ZenML stack](https://docs.zenml.io/stacks) is a collection of components that together form an MLOps infrastructure to run your ML pipelines. While your pipeline code defines what happens in your ML workflow, the stack determines where and how that code runs.

Stacks provide several key benefits:

1. **Environment Flexibility**: Run the same pipeline code locally during development and in the cloud for production
2. **Infrastructure Separation**: Change your infrastructure without modifying your pipeline code
3. **Specialized Resources**: Use specialized tools for different aspects of your ML workflow
4. **Team Collaboration**: Share infrastructure configurations across your team
5. **Reproducibility**: Ensure consistent pipeline execution across different environments

### Stack Structure

Each ZenML stack must include these core components:

* **Orchestrator**: Controls how your pipeline steps are executed
* **Artifact Store**: Manages where your pipeline artifacts are stored

Stacks may also include these optional components:

* **Container Registry**: Stores Docker images for your pipeline steps
* **Deployer**: Deploys pipelines as long-running HTTP services
* **Step Operator**: Runs specific steps on specialized hardware
* **Model Deployer**: Deploys models as prediction services
* **Experiment Tracker**: Tracks metrics and parameters
* **Feature Store**: Manages ML features
* **Alerter**: Sends notifications about pipeline events
* **Annotator**: Manages data labeling workflows

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
    -artifact-store s3-store \
    --orchestrator kubeflow \
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

* Learn about [deploying stacks](https://docs.zenml.io/stacks/deployment) on cloud platforms
* Understand [Service Connectors](service_connectors.md) for authenticating with cloud services
* Explore how to [register existing cloud resources](https://docs.zenml.io/how-to/infrastructure-deployment/stack-deployment/register-a-cloud-stack) as ZenML stack components
