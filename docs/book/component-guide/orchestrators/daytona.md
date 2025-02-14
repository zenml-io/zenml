---
description: Orchestrating your pipelines to run on Daytona.
---

# Daytona Orchestrator

The Daytona orchestrator is an integration provided by ZenML that allows you to run your pipelines on Daytona's infrastructure, leveraging its scalable compute resources and managed environment.

{% hint style="warning" %}
This component is only meant to be used within the context of a [remote ZenML deployment scenario](../../getting-started/deploying-zenml/README.md). Usage with a local ZenML deployment may lead to unexpected behavior!
{% endhint %}

## When to use it

* You are looking for a fast and easy way to run your pipelines on Daytona's infrastructure.
* You're already using Daytona for your machine learning projects.
* You want to leverage Daytona's managed infrastructure for running your pipelines.
* You're looking for a solution that simplifies the deployment and scaling of your ML workflows.

## How to deploy it

To use the Daytona orchestrator, you need to have a Daytona account and the necessary credentials. You don't need to deploy any additional infrastructure, as the orchestrator will use Daytona's managed resources.

## How it works

The Daytona orchestrator is a ZenML orchestrator that runs your pipelines on Daytona's infrastructure. When you run a pipeline with the Daytona orchestrator, ZenML will archive your current ZenML repository and upload it to the Daytona platform. Once the code is archived, ZenML will create a new environment in Daytona and upload the code to it. Then ZenML runs a list of commands to prepare for the pipeline run (e.g., installing dependencies, setting up the environment). Finally, ZenML will run the pipeline on Daytona's infrastructure.

* The orchestrator supports both CPU and GPU machine types. You can specify the machine type in the `DaytonaOrchestratorSettings`.

## How to use it

To use the Daytona orchestrator, you need:

* The ZenML `daytona` integration installed. If you haven't done so, run

```shell
zenml integration install daytona
```

* A [remote artifact store](../artifact-stores/artifact-stores.md) as part of your stack.

* Daytona credentials

### Daytona credentials

You will need the following credentials to use the Daytona orchestrator:

* `DAYTONA_API_KEY`: Your Daytona API key
* `DAYTONA_SERVER_URL`: Your Daytona server URL

You can set these credentials as environment variables or you can set them when registering the orchestrator:

```shell
zenml orchestrator register daytona_orchestrator \
    --flavor=daytona \
    --api_key=<YOUR_DAYTONA_API_KEY> \
    --server_url=<YOUR_DAYTONA_SERVER_URL>
```

We can then register the orchestrator and use it in our active stack:

```bash
# Register and activate a stack with the new orchestrator
zenml stack register daytona_stack -o daytona_orchestrator ... --set
```

You can configure the orchestrator at pipeline level, using the `orchestrator` parameter.

```python
from zenml.integrations.daytona.flavors import DaytonaOrchestratorSettings


daytona_settings = DaytonaOrchestratorSettings(
    machine_type="cpu",
    custom_commands=["pip install -r requirements.txt", "do something else"]
)

@pipeline(

## Settings

The `DaytonaOrchestratorSettings` allows you to configure various aspects of the orchestrator:

* `api_key`: The API key for authenticating with Daytona.
* `server_url`: The server URL for connecting to Daytona.
* `machine_type`: The type of machine to use (e.g., "cpu", "gpu").
* `custom_commands`: A list of custom commands to run before executing the pipeline.
* `synchronous`: Whether to run the pipeline synchronously or asynchronously.
* `image`: The Docker image to use for running the pipeline.
* `cpu`: The number of CPU cores to allocate.
* `memory`: The amount of memory to allocate (in MB).
* `disk`: The amount of disk space to allocate (in GB).
* `gpu`: The number of GPUs to allocate.
* `timeout`: The maximum time to wait for the pipeline to complete (in seconds).
* `auto_stop_interval`: The time interval after which the environment will be automatically stopped if idle (in seconds).

```bash
zenml pipeline run <pipeline-name>
```

## Monitoring and Logs

- Logs are available in the Daytona workspace.
- For asynchronous execution, check the `pipeline.log` file in the workspace.

## Advanced Configuration

- Customize resource allocation (CPU, memory, etc.) based on your pipeline needs.
- Use custom commands to set up the environment in the workspace.

For more details, refer to the [Daytona SDK documentation](https://daytona.work/docs). 