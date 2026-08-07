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

Most component types appear at most once in a stack. Three component types are
repeatable: **step operators**, **experiment trackers**, and **alerters**. If a
stack has more than one component of one of these types, the first attached
component is the default. You can still choose a non-default component by name
in step or pipeline configuration, and you can change the default later with
`zenml stack set-default`.

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
    --artifact-store s3-store \
    --orchestrator kubeflow \
    --container-registry ecr-registry \
    --experiment-tracker mlflow-tracker

# Attach multiple repeatable components. The first one becomes the default.
zenml stack register training-stack \
    --artifact-store s3-store \
    --orchestrator kubernetes \
    --step_operator gpu-step-operator \
    --step_operator cpu-step-operator \
    --experiment_tracker mlflow \
    --experiment_tracker wandb

# Promote a different attached component to be the default.
zenml stack set-default training-stack --step_operator cpu-step-operator
```

### Discovering flavor-specific configuration

Stack component flavors have different configuration fields. A local
orchestrator needs very little information; a Kubernetes orchestrator needs
cluster and namespace details; an S3 artifact store needs bucket information.
Once you pass a flavor with `-f` / `--flavor`, the CLI can show the concrete
configuration fields for that flavor:

```bash
zenml orchestrator register -f kubernetes --help
zenml artifact-store register -f s3 --help
zenml step-operator update my-runai-step-operator --help
```

The help output includes a **Flavor configuration** section. For register and
update commands, pass those fields as `--name=value` arguments. This is often
the fastest way to answer, "what exactly does this flavor need from me?"

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

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
