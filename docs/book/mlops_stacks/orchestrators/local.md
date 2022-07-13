---
description: Orchestrate pipelines locally
---

The local orchestrator is an [orchestrator](./overview.md) flavor which comes built-in with 
ZenML and runs your pipelines locally.

## When to use it

You should use the local orchestrator if:
* ...

## How to deploy it

The local orchestrator comes with ZenML and works without any additional setup.

## How to use it

To use the local orchestrator, we can register it and use it in our active stack:
```shell
zenml orchestrator register <NAME> --flavor=local

# Add the orchestrator to the active stack
zenml stack update -o <NAME>
```

TODO: explain how to run a pipeline

For more information and a full list of configurable attributes of the local orchestrator, check out the 
[API Docs](https://apidocs.zenml.io/latest/api_docs/orchestrators/#zenml.orchestrators.local.local_orchestrator.LocalOrchestrator).