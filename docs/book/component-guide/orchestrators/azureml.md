---
description: Orchestrating your pipelines to run on AzureML.
---

# AzureML Orchestrator

[AzureML](https://azure.microsoft.com/en-us/products/machine-learning) is a
cloud-based orchestration service provided by Microsoft, that enables 
data scientists, machine learning engineers, and developers to build, train, 
deploy, and manage machine learning models. It offers a comprehensive and 
integrated environment that supports the entire machine learning lifecycle, 
from data preparation and model development to deployment and monitoring.

## When to use it

You should use the AzureML orchestrator if:

* you're already using Azure.
* you're looking for a proven production-grade orchestrator.
* you're looking for a UI in which you can track your pipeline runs.
* you're looking for a managed solution for running your pipelines.

## How it works

The ZenML AzureML orchestrator implementation uses [the Python SDK v2 of 
AzureML](https://learn.microsoft.com/en-gb/python/api/overview/azure/ai-ml-readme?view=azure-python) 
to allow our users to build their Machine Learning pipelines. For each ZenML step,
it creates an AzureML [CommandComponent](https://learn.microsoft.com/en-us/python/api/azure-ai-ml/azure.ai.ml.entities.commandcomponent?view=azure-python)
and brings them together in a pipeline.

## How to deploy it

{% hint style="info" %}
Would you like to skip ahead and deploy a full ZenML cloud stack already,
including an AzureML orchestrator? Check out the [in-browser stack deployment wizard](../../how-to/infrastructure-deployment/stack-deployment/deploy-a-cloud-stack.md),
the [stack registration wizard](../../how-to/infrastructure-deployment/stack-deployment/register-a-cloud-stack.md),
or [the ZenML Azure Terraform module](../../how-to/infrastructure-deployment/stack-deployment/deploy-a-cloud-stack-with-terraform.md)
for a shortcut on how to deploy & register this stack component.
{% endhint %}

In order to use an AzureML orchestrator, you need to first 
deploy [ZenML to the cloud](../../getting-started/deploying-zenml/README.md). 
It would be recommended to deploy ZenML in the same region as you plan on 
using for AzureML, but it is not necessary to do so. You must ensure that 
you are [connected to the remote ZenML server](../../how-to/connecting-to-zenml/connect-in-with-your-user-interactive.md)
before using this stack component.

## How to use it

In order to use the AzureML orchestrator, you need:

* The ZenML `azure` integration installed. If you haven't done so, run:

```shell
zenml integration install azure
```

* [Docker](https://www.docker.com) installed and running or a remote image builder in your stack.
* A [remote artifact store](../artifact-stores/artifact-stores.md) as part of your stack.
* A [remote container registry](../container-registries/container-registries.md) as part of your stack.
* An [Azure resource group equipped with an AzureML workspace](https://learn.microsoft.com/en-us/azure/machine-learning/quickstart-create-resources?view=azureml-api-2) to run your pipeline on.

There are two ways of authenticating your orchestrator with AzureML:

1. **Default Authentication** simplifies the authentication process while 
developing your workflows that deploy to Azure by combining credentials used in 
Azure hosting environments and credentials used in local development.
2. **Service Principal Authentication (recommended)** is using the concept 
of service principals on Azure to allow you to connect your cloud components 
with proper authentication. For this method, you will need to [create a service 
principal on Azure](https://learn.microsoft.com/en-us/azure/developer/python/sdk/authentication-on-premises-apps?tabs=azure-portal), 
assign it the correct permissions and use it to [register a ZenML Azure Service Connector](../../how-to/infrastructure-deployment/auth-management/azure-service-connector.md).
    ```bash
    zenml service-connector register <CONNECTOR_NAME> --type azure -i
    zenml orchestrator connect <ORCHESTRATOR_NAME> -c <CONNECTOR_NAME>
    ```

## Docker

For each pipeline run, ZenML will build a Docker image called 
`<CONTAINER_REGISTRY_URI>/zenml:<PIPELINE_NAME>` which includes your code 
and use it to run your pipeline steps in AzureML. Check out 
[this page](../../how-to/customize-docker-builds/README.md) if you want to 
learn more about how ZenML builds these images and how you can customize them.

## AzureML UI

Each AzureML workspace comes equipped with an Azure Machine Learning studio. 
Here you can inspect, manage, and debug your pipelines and steps.

![AzureML pipeline example](../../.gitbook/assets/azureml-pipelines.png)

Double-clicking any of the steps on this view will open up the overview page 
for that specific step. Here you can check the configuration of the component 
and its execution logs.

## Settings

The ZenML AzureML orchestrator comes with a dedicated class called 
`AzureMLOrchestratorSettings` for configuring its settings, and it controls
the compute resources used for pipeline execution in AzureML.

Currently, it supports three different modes of operation.

### 1. Serverless Compute (Default)
- Set `mode` to `serverless`.
- Other parameters are ignored.

**Example:**

```python
from zenml import step, pipeline
from zenml.integrations.azure.flavors import AzureMLOrchestratorSettings

azureml_settings = AzureMLOrchestratorSettings(
  mode="serverless"  # It's the default behavior
)

@step
def example_step() -> int:
    return 3


@pipeline(settings={"orchestrator": azureml_settings})
def pipeline():
    example_step()

pipeline()
```

### 2. Compute Instance
- Set `mode` to `compute-instance`.
- Requires a `compute_name`.
  - If a compute instance with the same name exists, it uses the existing 
  compute instance and ignores other parameters. (It will throw a warning if the 
  provided configuration does not match the existing instance.)
  - If a compute instance with the same name doesn't exist, it creates a 
  new compute instance with the `compute_name`. For this process, you can 
  specify `size` and `idle_type_before_shutdown_minutes`.

**Example:**

```python
from zenml import step, pipeline
from zenml.integrations.azure.flavors import AzureMLOrchestratorSettings

azureml_settings = AzureMLOrchestratorSettings(
    mode="compute-instance",
    compute_name="my-gpu-instance",  # Will fetch or create this instance
    size="Standard_NC6s_v3",  # Using a NVIDIA Tesla V100 GPU
    idle_time_before_shutdown_minutes=20,
)

@step
def example_step() -> int:
    return 3


@pipeline(settings={"orchestrator": azureml_settings})
def pipeline():
    example_step()

pipeline()
```

### 3. Compute Cluster
- Set `mode` to `compute-cluster`.
- Requires a `compute_name`.
  - If a compute cluster with the same name exists, it uses existing cluster, 
  ignores other parameters. (It will throw a warning if the provided 
  - configuration does not match the existing cluster.)
  - If a compute cluster with the same name doesn't exist, it creates a new 
  compute cluster. Additional parameters can be used for configuring this 
  process.

**Example:**

```python
from zenml import step, pipeline
from zenml.integrations.azure.flavors import AzureMLOrchestratorSettings

azureml_settings = AzureMLOrchestratorSettings(
    mode="compute-cluster",
    compute_name="my-gpu-cluster",  # Will fetch or create this instance
    size="Standard_NC6s_v3",  # Using a NVIDIA Tesla V100 GPU
    tier="Dedicated",  # Can be set to either "Dedicated" or "LowPriority"
    min_instances=2,
    max_instances=10,
    idle_time_before_scaledown_down=60,
)

@step
def example_step() -> int:
    return 3


@pipeline(settings={"orchestrator": azureml_settings})
def pipeline():
    example_step()

pipeline()
```

{% hint style="info" %}
In order to learn more about the supported sizes for compute instances and 
clusters, you can check [the AzureML documentation](https://learn.microsoft.com/en-us/azure/machine-learning/concept-compute-target?view=azureml-api-2#supported-vm-series-and-sizes).
{% endhint %}

### Run pipelines on a schedule

The AzureML orchestrator supports running pipelines on a schedule using 
its [JobSchedules](https://learn.microsoft.com/en-us/azure/machine-learning/how-to-schedule-pipeline-job?view=azureml-api-2&tabs=python). 
Both cron expression and intervals are supported.

```python
from zenml.config.schedule import Schedule

# Run a pipeline every 5th minute
pipeline.run(schedule=Schedule(cron_expression="*/5 * * * *"))
```

Once you run the pipeline with a schedule, you can find the schedule and 
the corresponding run under the `All Schedules` tab `Jobs` in the jobs page
on AzureML.

{% hint style="warning" %}
Note that ZenML only gets involved to schedule a run, but maintaining the 
lifecycle of the schedule is the responsibility of the user. That means, if you 
want to cancel a schedule that you created on AzureML, you will have to do 
it through the Azure UI.
{% endhint %}

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
