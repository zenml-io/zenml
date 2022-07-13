---
description: Orchestrate pipelines with Kubeflow
---

The Kubeflow orchestrator is an [orchestrator](./overview.md) flavor provided with
the ZenML `kubeflow` integration that uses [Kubeflow](https://www.kubeflow.org/)
to run your pipelines.

## When to use it

You should use the Kubeflow orchestrator if:
* ...

## How to deploy it

...

## How to use it

To use the Kubeflow orchestrator, we need:
* The ZenML `kubeflow` integration installed. If you haven't done so, run 
    ```shell
    zenml integration install kubeflow
    ```

We can then register the orchestrator and use it in our active stack:
```shell
zenml orchestrator register <NAME> \
    --flavor=kubeflow

# Add the orchestrator to the active stack
zenml stack update -o <NAME>
```

TODO: explain how to run a pipeline

A concrete example of using the Kubeflow orchestrator can be found 
[here](https://github.com/zenml-io/zenml/tree/main/examples/kubeflow_pipelines_orchestration).

For more information and a full list of configurable attributes of the Kubeflow orchestrator, check out the 
[API Docs](https://apidocs.zenml.io/latest/api_docs/integrations/#zenml.integrations.kubeflow.orchestrators.kubeflow_orchestrator.KubeflowOrchestrator).