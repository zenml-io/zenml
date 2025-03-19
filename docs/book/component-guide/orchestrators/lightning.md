---
description: Orchestrating your pipelines to run on Lightning AI.
---

# Lightning AI Orchestrator

[Lightning AI Studio](https://lightning.ai/) is a platform that simplifies the development and deployment of AI applications. The Lightning AI orchestrator is an integration provided by ZenML that allows you to run your pipelines on Lightning AI's infrastructure, leveraging its scalable compute resources and managed environment.

{% hint style="warning" %}
This component is only meant to be used within the context of a [remote ZenML deployment scenario](https://docs.zenml.io/getting-started/deploying-zenml/). Usage with a local ZenML deployment may lead to unexpected behavior!
{% endhint %}

## When to use it

* You are looking for a fast and easy way to run your pipelines on GPU instances
* You're already using Lightning AI for your machine learning projects
* You want to leverage Lightning AI's managed infrastructure for running your pipelines
* You're looking for a solution that simplifies the deployment and scaling of your ML workflows
* You want to take advantage of Lightning AI's optimizations for machine learning workloads

## How to deploy it

To use the [Lightning AI Studio](https://lightning.ai/) orchestrator, you need to have a Lightning AI account and the necessary credentials. You don't need to deploy any additional infrastructure, as the orchestrator will use Lightning AI's managed resources.

## How it works

The Lightning AI orchestrator is a ZenML orchestrator that runs your pipelines on Lightning AI's infrastructure. When you run a pipeline with the Lightning AI orchestrator, ZenML will archive your current ZenML repository and upload it to the Lightning AI studio. Once the code is archived, using `lightning-sdk`, ZenML will create a new stduio in Lightning AI and upload the code to it. Then ZenML runs list of commands via `studio.run()` to prepare for the pipeline run (e.g. installing dependencies, setting up the environment). Finally, ZenML will run the pipeline on Lightning AI's infrastructure.

* You can always use an already existing studio by specifying the `main_studio_name` in the `LightningOrchestratorSettings`.
* The orchestartor supports a async mode, which means that the pipeline will be run in the background and you can check the status of the run in the ZenML Dashboard or the Lightning AI Studio.
* You can specify a list of custom commands that will be executed before running the pipeline. This can be useful for installing dependencies or setting up the environment.
* The orchestrator supports both CPU and GPU machine types. You can specify the machine type in the `LightningOrchestratorSettings`.

## How to use it

To use the Lightning AI orchestrator, you need:

* The ZenML `lightning` integration installed. If you haven't done so, run

```shell
zenml integration install lightning
```

* A [remote artifact store](https://docs.zenml.io/stacks/artifact-stores/) as part of your stack.
* [Lightning AI credentials](lightning.md#lightning-ai-credentials)

### Lightning AI credentials

You will need the following credentials to use the Lightning AI orchestrator:

* `LIGHTNING_USER_ID`: Your Lightning AI user ID
* `LIGHTNING_API_KEY`: Your Lightning AI API key
* `LIGHTNING_USERNAME`: Your Lightning AI username (optional)
* `LIGHTNING_TEAMSPACE`: Your Lightning AI teamspace (optional)
* `LIGHTNING_ORG`: Your Lightning AI organization (optional)

To find these credentials, log in to your [Lightning AI](https://lightning.ai/) account and click on your avatar in the top right corner. Then click on "Global Settings". There are some tabs you can click on the left hand side. Click on the one that says "Keys" and you will see two ways to get your credentials. The 'Login via CLI' will give you the `LIGHTNING_USER_ID` and `LIGHTNING_API_KEY`.

You can set these credentials as environment variables or you can set them when registering the orchestrator:

```shell
zenml orchestrator register lightning_orchestrator \
    --flavor=lightning \
    --user_id=<YOUR_LIGHTNING_USER_ID> \
    --api_key=<YOUR_LIGHTNING_API_KEY> \
    --username=<YOUR_LIGHTNING_USERNAME> \ # optional
    --teamspace=<YOUR_LIGHTNING_TEAMSPACE> \ # optional
    --organization=<YOUR_LIGHTNING_ORGANIZATION> # optional
```

We can then register the orchestrator and use it in our active stack:

```bash
# Register and activate a stack with the new orchestrator
zenml stack register lightning_stack -o lightning_orchestrator ... --set
```

You can configure the orchestrator at pipeline level, using the `orchestrator` parameter.

```python
from zenml.integrations.lightning.flavors.lightning_orchestrator_flavor import LightningOrchestratorSettings


lightning_settings = LightningOrchestratorSettings(
    main_studio_name="my_studio",
    machine_type="cpu",
    async_mode=True,
    custom_commands=["pip install -r requirements.txt", "do something else"]
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
ZenML will archive the current zenml repository (the code within the path where you run `zenml init`) and upload it to the Lightning AI studio. For this reason you need make sure that you have run `zenml init` in the same repository root directory where you are running your pipeline.
{% endhint %}

![Lightning AI studio VSCode](../../.gitbook/assets/lightning_studio_vscode.png)

{% hint style="info" %}
The `custom_commands` attribute allows you to specify a list of shell commands that will be executed before running the pipeline. This can be useful for installing dependencies or setting up the environment, The commands will be executed in the root directory of the uploaded and extracted ZenML repository.
{% endhint %}

You can now run any ZenML pipeline using the Lightning AI orchestrator:

```shell
python file_that_runs_a_zenml_pipeline.py
```

### Lightning AI UI

Lightning AI provides its own UI where you can monitor and manage your running applications, including the pipelines orchestrated by ZenML.

![Lightning AI Studio](../../.gitbook/assets/lightning_studio_ui.png)

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
    main_studio_name="my_studio",
    machine_type="cpu",
    async_mode=True,
    custom_commands=["pip install -r requirements.txt", "do something else"]
)
```

These settings can then be specified on either a pipeline-level or step-level:

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

Check out the [SDK docs](https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-lightning.html#zenml.integrations.lightning) for a full list of available attributes and [this docs page](https://docs.zenml.io/how-to/pipeline-development/use-configuration-files/runtime-configuration) for more information on how to specify settings.

To use GPUs with the Lightning AI orchestrator, you need to specify a GPU-enabled machine type in your settings:

```python
lightning_settings = LightningOrchestratorSettings(
    machine_type="gpu", # or `A10G` e.g.
)
```

Make sure to check [Lightning AI's documentation](https://lightning.ai/docs/overview/studios/change-gpus) for the available GPU-enabled machine types and their specifications.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
