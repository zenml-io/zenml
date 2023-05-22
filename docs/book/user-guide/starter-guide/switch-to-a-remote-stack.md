---
description: Bring your pipelines into production using cloud stacks.
---

# Switch to a remote stack

## Switch to a Remote Stack

In order to bring your pipelines into production using cloud stacks, you need to configure and register stack components and stacks. This guide will walk you through the process of registering stack components, registering a stack, activating a stack, changing stacks, accessing the active stack in Python, and unregistering stacks.

Before diving into the steps, it's important to note that you will need access to a ZenML Deployment. If you don't have one set up yet, don't worry! ZenML provides a managed Sandbox environment with a pre-configured remote stack for users to try out its features without setting up their own infrastructure. You can learn more about the ZenML Sandbox later in this guide.

### High-Level Overview

Switching to a remote stack involves several key steps:

1. Registering Stack Components: Configure each tool as a stack component with the desired flavor.
2. Registering a Stack: Combine registered stack components into one stack.
3. Activating a Stack: Set the registered stack as active for your pipelines.
4. Changing Stacks: Switch between multiple configured stacks as needed.
5. Accessing the Active Stack in Python: Retrieve or modify information of your active stack and its components programmatically.
6. Unregistering Stacks: Remove registered stacks and their components when no longer needed.

Throughout this guide, we will use practical examples with commands based on the ZenML Sandbox environment.

### Registering Stack Components

First, you need to create a new instance of the respective stack component with the desired flavor using `zenml <STACK_COMPONENT> register <NAME> --flavor=<FLAVOR>`. Most flavors require further parameters that you can pass as additional argument `--param=value`, similar to how we passed the flavor.

For example, let's assume you have access to a ZenML Sandbox environment. You can register an _S3_ artifact store using the following command:

```shell
zenml artifact-store register <ARTIFACT_STORE_NAME> \
    --flavor=s3 \
    --bucket=<SANDBOX_BUCKET_NAME> \
    --access_key=<SANDBOX_ACCESS_KEY> \
    --secret_key=<SANDBOX_SECRET_KEY>
```

After registering, you should be able to see the new artifact store in the list of registered artifact stores, which you can access using the following command:

```shell
zenml artifact-store list
```

### Registering a Stack

After registering each tool as the respective stack components, you can combine all of them into one stack using the `zenml stack register` command:

```shell
zenml stack register <STACK_NAME> \
    --orchestrator <ORCHESTRATOR_NAME> \
    --artifact-store <ARTIFACT_STORE_NAME> \
    ...
```

For example, with your ZenML Sandbox environment, you can register a stack that includes the S3 artifact store you registered earlier:

```shell
zenml stack register sandbox_stack \
    --orchestrator kubeflow_orchestrator \
    --artifact-store s3_artifact_store
```

### Activating a Stack

Finally, to start using the stack you just registered, set it as active:

```shell
zenml stack set <STACK_NAME>
```

Now all your code is automatically executed using this stack.

### Changing Stacks

If you have multiple stacks configured, you can switch between them using the `zenml stack set` command, similar to how you activate a stack.

### Accessing the Active Stack in Python

The following code snippet shows how you can retrieve or modify information of your active stack and stack components in Python:

```python
from zenml.client import Client

client = Client()
active_stack = client.active_stack
print(active_stack.name)
print(active_stack.orchestrator.name)
print(active_stack.artifact_store.name)
print(active_stack.artifact_store.path)
```

### Unregistering Stacks

To unregister (delete) a stack and all of its components, run

```shell
zenml stack delete <STACK_NAME>
```

to delete the stack itself, followed by

```shell
zenml <STACK_COMPONENT> delete <STACK_COMPONENT_NAME>
```

### ZenML Sandbox

As mentioned earlier, ZenML provides a managed Sandbox environment with a pre-configured remote stack for users to try out its features without setting up their own infrastructure. The ZenML Sandbox is a great resource for learning how to switch to a remote stack and experiment with different configurations. This managed infrastructure deployed on Kubernetes includes a Kubeflow Orchestrator, MLflow Experiment Tracker, and MinIO Object Storage. This isolated environment enables users to explore and experiment with ZenML's features without the need for setting up and managing their own infrastructure. Each sandbox is only available for a maximum of 8 hours, and users can create one sandbox at a time.

### Getting Started with ZenML Sandbox

#### Step 1: Sign up

To start using the ZenML Sandbox, sign up with your Google account. This will create a new sandbox environment for you to explore ZenML and its features.

#### Step 2: Access credentials

After signing up and creating your sandbox, you will be provided with credentials for Kubeflow, MinIO, MLflow, and ZenML. These credentials will allow you to access and interact with the various applications and services within the sandbox.

#### Step 3: Connect and set the stack

Use the `zenml connect` command to connect your local ZenML installation to the sandbox environment. Then, use the `zenml stack set` command to set the appropriate stack for your sandbox.

```bash
zenml connect --url <sandbox_url> --username <username>
zenml stack set <stack_name>
```

#### Step 4: Explore pre-built pipelines

The ZenML Sandbox provides a repository of pre-built pipelines that users can choose from to run on their sandbox. Users can access these pipelines through the ZenML Sandbox interface and run them using the provided credentials for Kubeflow, MLflow, and ZenML.

#### Step 5: Run pipelines

To run a pipeline in the sandbox, use the `python run.py` command. You can either clone a repository with the pipelines or use a special ZenML command to run them, to be decided.

```bash
python run.py
```

#### Step 6: Sandbox deletion

After 8 hours, your sandbox will be automatically deleted. Make sure to save any important data or results before the sandbox is deleted. While the sandbox is active, you can also delete it manually through the ZenML Sandbox interface.

### Sandbox Frequently Asked Questions

**Q: Can I create more than one sandbox at a time?**

A: No, each user can create only one sandbox at a time. Once your current sandbox is deleted, you can create a new one.

**Q: Can I extend the 8-hour limit for my sandbox?**

A: The 8-hour limit is fixed and cannot be extended. However, you can create a new sandbox after your current one is deleted.

**Q: Can I use my own pipelines in the ZenML Sandbox?**

A: The ZenML Sandbox is designed for users to explore ZenML using pre-built example pipelines. While it is possible to use your own pipelines, however, we do not recommend it as the sandbox is not designed for this purpose, since every user is provided with limited resources.

**Q: Are there any model deployment options available in the ZenML Sandbox?**

A: At the moment, there are no model deployment tools available in the ZenML Sandbox. However, we are working on adding this feature in the future.
