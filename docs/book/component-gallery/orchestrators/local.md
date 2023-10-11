---
description: How to orchestrate pipelines locally
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


The local orchestrator is an [orchestrator](./orchestrators.md) flavor which 
comes built-in with ZenML and runs your pipelines locally.

## When to use it

The local orchestrator is part of your default stack when you're first getting 
started with ZenML. Due to it running locally on your machine, it requires 
no additional setup and is easy to use and debug.

You should use the local orchestrator if:
* you're just getting started with ZenML and want to run pipelines
without setting up any cloud infrastructure.
* you're writing a new pipeline and want to experiment and debug quickly

## How to deploy it

The local orchestrator comes with ZenML and works without any additional setup.

## How to use it

To use the local orchestrator, we can register it and use it in our active stack:

```shell
zenml orchestrator register <NAME> --flavor=local

# Add the orchestrator to the active stack
zenml stack update -o <NAME>
```

You can now run any ZenML pipeline using the local orchestrator:

```shell
python file_that_runs_a_zenml_pipeline.py
```

For more information and a full list of configurable attributes of the local 
orchestrator, check out the [API Docs](https://apidocs.zenml.io/latest/core_code_docs/core-orchestrators/#zenml.orchestrators.local.local_orchestrator.LocalOrchestrator).