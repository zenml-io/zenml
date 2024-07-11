---
description: Orchestrating your pipelines to run on Databricks.
---

# Databricks Orchestrator

[Databricks](https://www.databricks.com/) is a unified data analytics platform that combines the best of data warehouses and data lakes to offer an integrated solution for big data processing and machine learning. It provides a collaborative environment for data scientists, data engineers, and business analysts to work together on data projects. Databricks is built on top of Apache Spark, offering optimized performance and scalability for big data workloads.

The Databricks orchestrator is an orchestrator flavor provided by the ZenML databricks integration that allows you to run your pipelines on Databricks. This integration enables you to leverage Databricks' powerful distributed computing capabilities and optimized environment for your ML pipelines within the ZenML framework.

{% hint style="warning" %}
This component is only meant to be used within the context of a [remote ZenML deployment scenario](../../getting-started/deploying-zenml/README.md). Usage with a local ZenML deployment may lead to unexpected behavior!
{% endhint %}

### When to use it

You should use the Databricks orchestrator if:

* you're already using Databricks for your data and ML workloads.
* you want to leverage Databricks' powerful distributed computing capabilities for your ML pipelines.
* you're looking for a managed solution that integrates well with other Databricks services.
* you want to take advantage of Databricks' optimization for big data processing and machine learning.

### Prerequisites

You will need to do the following to start using the Databricks orchestrator:

* An Active Databricks workspace
* Active Databricks account or service account with sufficiant permession to create and run jobs


## How it works

The HyperAI orchestrator works with Wheel Packages. Under the hood, ZenML Creates a python wheel from your project that get's uploaded to databricks to be executed, it also creates 
a job using Databricks SDK, this databricks job definition contains all neccsary information such as the steps and ensure that pipeline steps will only run if their connected upstream steps have successfully finished., dependencies needed to run the pipeline and the provided extra configuration in case we want to run on gpu


### How to use it

To use the Databricks orchestrator, you first need to register it and add it to your stack, we must configure the host and a client_id and client_secret as authentication methods. For example, we can register the orchestrator and use it in our active stack:

```shell
zenml orchestrator register databricks_orchestrator --flavor=databricks --host="https://xxxxx.x.azuredatabricks.net" --client_id={{databricks.client_id}} --client_secret={{databricks.client_secret}}

# Add the orchestrator to your stack
zenml stack register databricks_stack -o databricks_orchestrator ... --set
```

You can now run any ZenML pipeline using the HyperAI orchestrator:

```shell
python run.py
```

### Databricks UI

Databricks comes with its own UI that you can use to find further details about your pipeline runs, such as the logs of your steps.

![Databricks UI](../../.gitbook/assets/DatabricksUI.png)

For any runs executed on Databricks, you can get the URL to the Databricks UI in Python using the following code snippet:

```python
from zenml.client import Client

pipeline_run = Client().get_pipeline_run("<PIPELINE_RUN_NAME>")
orchestrator_url = pipeline_run.run_metadata["orchestrator_url"].value
```

### Additional configuration

For additional configuration of the Databricks orchestrator, you can pass `DatabricksOrchestratorSettings` which allows you to configure node selectors, affinity, and tolerations to apply to the Kubernetes Pods running your pipeline. These can be either specified using the Kubernetes model objects or as dictionaries.

```python
from zenml.integrations.databricks.flavors.databricks_orchestrator_flavor import DatabricksOrchestratorSettings

databricks_settings = DatabricksOrchestratorSettings(
    spark_version="15.3.x-scala2.12"
    num_workers="3"
    node_type_id="Standard_D4s_v5"
    policy_id=POLICY_ID
    autoscale=(2, 3)
    spark_conf={}
    spark_env_vars={}
)
```

These settings can then be specified on either pipeline-level or step-level:

```python
# Either specify on pipeline-level
@pipeline(
    settings={
        "orchestrator.databricks": databricks_settings,
    }
)
def my_pipeline():
    ...
```

#### Enabling CUDA for GPU-backed hardware

Note that if you wish to use this orchestrator to run steps on a GPU, you will need to follow [the instructions on this page](../../how-to/training-with-gpus/training-with-gpus.md) to ensure that it works. It requires adding some extra settings customization and is essential to enable CUDA for the GPU to give its full acceleration.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>


Check out the [SDK docs](https://sdkdocs.zenml.io/latest/integration\_code\_docs/integrations-databricks/#zenml.integrations.databricks.flavors.databricks\_orchestrator\_flavor.DatabricksOrchestratorSettings) for a full list of available attributes and [this docs page](../../how-to/use-configuration-files/runtime-configuration.md) for more information on how to specify settings.

For more information and a full list of configurable attributes of the Databricks orchestrator, check out the [SDK Docs](https://sdkdocs.zenml.io/latest/integration\_code\_docs/integrations-databricks/#zenml.integrations.databricks.orchestrators.databricks\_orchestrator.DatabricksOrchestrator) .