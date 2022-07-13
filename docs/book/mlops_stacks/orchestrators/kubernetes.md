---
description: Orchestrate pipelines with Kubernetes
---

The Kubernetes orchestrator is an [orchestrator](./overview.md) flavor provided with
the ZenML `kubernetes` integration that runs your pipelines on a 
[Kubernetes](https://kubernetes.io/) cluster.

## When to use it

You should use the Kubernetes orchestrator if:
* ...

## How to deploy it

...

## How to use it

To use the Kubernetes orchestrator, we need:
* The ZenML `kubernetes` integration installed. If you haven't done so, run 
    ```shell
    zenml integration install kubernetes
    ```

We can then register the orchestrator and use it in our active stack:
```shell
zenml orchestrator register <NAME> \
    --flavor=kubernetes

# Add the orchestrator to the active stack
zenml stack update -o <NAME>
```

TODO: explain how to run a pipeline

A concrete example of using the Kubernetes orchestrator can be found 
[here](https://github.com/zenml-io/zenml/tree/main/examples/kubernetes_orchestration).

For more information and a full list of configurable attributes of the Kubernetes orchestrator, check out the 
[API Docs](https://apidocs.zenml.io/latest/api_docs/integrations/#zenml.integrations.kubernetes.orchestrators.kubernetes_orchestrator.KubernetesOrchestrator).