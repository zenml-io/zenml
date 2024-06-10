---
description: Orchestrating your pipelines to run locally.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Local Orchestrator

The local orchestrator is an [orchestrator](./orchestrators.md) flavor that comes built-in with ZenML and runs your pipelines locally.

### When to use it

The local orchestrator is part of your default stack when you're first getting started with ZenML. Due to it running locally on your machine, it requires no additional setup and is easy to use and debug.

You should use the local orchestrator if:

* you're just getting started with ZenML and want to run pipelines without setting up any cloud infrastructure.
* you're writing a new pipeline and want to experiment and debug quickly

### How to deploy it

The local orchestrator comes with ZenML and works without any additional setup.

### How to use it

To use the local orchestrator, we can register it and use it in our active stack:

```shell
zenml orchestrator register <ORCHESTRATOR_NAME> --flavor=local

# Register and activate a stack with the new orchestrator
zenml stack register <STACK_NAME> -o <ORCHESTRATOR_NAME> ... --set
```

You can now run any ZenML pipeline using the local orchestrator:

```shell
python file_that_runs_a_zenml_pipeline.py
```

For more information and a full list of configurable attributes of the local orchestrator, check out the [SDK Docs](https://sdkdocs.zenml.io/latest/core\_code\_docs/core-orchestrators/#zenml.orchestrators.local.local\_orchestrator.LocalOrchestrator) .

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
