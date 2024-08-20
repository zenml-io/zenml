
---
description: Orchestrating your pipelines to run on Lightning AI.
---


# Lightning AI Orchestrator

[Lightning AI](https://lightning.ai/) is a platform that simplifies the development and deployment of AI applications. The Lightning AI orchestrator is an integration provided by ZenML that allows you to run your pipelines on Lightning AI's infrastructure, leveraging its scalable compute resources and managed environment.


{% hint style="warning" %}
This component is only meant to be used within the context of a [remote ZenML deployment scenario](../../getting-started/deploying-zenml/README.md). Usage with a local ZenML deployment may lead to unexpected behavior!
{% endhint %}


## When to use it

* You are looking for a fast and easy way to run your pipelines on GPU instances.

* you're already using Lightning AI for your machine learning projects.

* you want to leverage Lightning AI's managed infrastructure for running your pipelines.


* you're looking for a solution that simplifies the deployment and scaling of your ML workflows.


* you want to take advantage of Lightning AI's optimizations for machine learning workloads.


## How to deploy it

To use the Lightning AI orchestrator, you need to have a Lightning AI account and the necessary credentials. You don't need to deploy any additional infrastructure, as the orchestrator will use Lightning AI's managed resources.


## How to use it

To use the Lightning AI orchestrator, you need:

*   The ZenML `lightning` integration installed. If you haven't done so, run

    ```shell
    zenml integration install lightning
    ```

* A [remote artifact store](../artifact-stores/artifact-stores.md) as part of your stack.


* [Lightning AI credentials](#lightning-ai-credentials)


### Lightning AI credentials

* `LIGHTNING_USER_ID`: Your Lightning AI user ID

* `LIGHTNING_API_KEY`: Your Lightning AI API key

* `LIGHTNING_USERNAME`: Your Lightning AI username (optional)

* `LIGHTNING_TEAMSPACE`: Your Lightning AI teamspace (optional)

* `LIGHTNING_ORG`: Your Lightning AI organization (optional)


Alternatively, you can configure these credentials when registering the orchestrator.


We can then register the orchestrator and use it in our active stack:

```shell
zenml orchestrator register lightning_orchestrator \
    --flavor=lightning \
    --user_id=<YOUR_LIGHTNING_USER_ID> \
    --api_key=<YOUR_LIGHTNING_API_KEY> \
    --username=<YOUR_LIGHTNING_USERNAME> \
    --teamspace=<YOUR_LIGHTNING_TEAMSPACE> \
    --organization=<YOUR_LIGHTNING_ORGANIZATION>

# Register and activate a stack with the new orchestrator
zenml stack register lightning_stack -o lightning_orchestrator ... --set
```

You can also configure the orchestrator at pipeline level, using the `orchestrator` parameter.


```python
from zenml.integrations.lightning.flavors.lightning_orchestrator_flavor import LightningOrchestratorSettings


lightning_settings = LightningOrchestratorSettings(
    machine_type="cpu",
    async_mode=True
)

@pipeline(
    settings={
        "orchestrator.lightning": lightning_settings
    }
)
def my_pipeline():
    ...
```


{% hint style="info" %}
ZenML will build a wheel that includes all the files within you zenml repository and upload it to the lightning studio.
For this reason you need make sure that you are running `zenml init` in the same directory where you are running your pipeline.
{% endhint %}


You can now run any ZenML pipeline using the Lightning AI orchestrator:

```shell
python file_that_runs_a_zenml_pipeline.py
```


### Lightning AI UI

Lightning AI provides its own UI where you can monitor and manage your running applications, including the pipelines orchestrated by ZenML.
For any runs executed on Lightning AI, you can get the URL to the Lightning AI UI in Python using the following code snippet:

```python
from zenml.client import Client

pipeline_run = Client().get_pipeline_run("<PIPELINE_RUN_NAME>")
orchestrator_url = pipeline_run.run_metadata["orchestrator_url"].value
```


### Additional configuration

For additional configuration of the Lightning AI orchestrator, you can pass `LightningOrchestratorSettings` which allows you to configure various aspects of the Lightning AI execution environment:

```python
from zenml.integrations.lightning.flavors.lightning_orchestrator_flavor import LightningOrchestratorSettings

lightning_settings = LightningOrchestratorSettings(
    machine_type="cpu",
    async_mode=True
)
```


These settings can then be specified on either pipeline-level or step-level:

```python
# Either specify on pipeline-level
@pipeline(
    settings={
        "orchestrator.lightning": lightning_settings
    }
)
def my_pipeline():
    ...

# OR specify settings on step-level
@step(
    settings={
        "orchestrator.lightning": lightning_settings
    }
)
def my_step():
    ...
```

Check out the [SDK docs](https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-lightning/#zenml.integrations.lightning.flavors.lightning_orchestrator_flavor.LightningOrchestratorSettings) for a full list of available attributes and [this docs page](../../how-to/use-configuration-files/runtime-configuration.md) for more information on how to specify settings.


To use GPUs with the Lightning AI orchestrator, you need to specify a GPU-enabled machine type in your settings:

```python
lightning_settings = LightningOrchestratorSettings(
    machine_type="gpu",
)
```


Make sure to check Lightning AI's documentation for the available GPU-enabled machine types and their specifications.


<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>