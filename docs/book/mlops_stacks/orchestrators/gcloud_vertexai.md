---
description: Orchestrate pipelines with Vertex AI
---

The Vertex orchestrator is an [orchestrator](./overview.md) flavor provided with
the ZenML `gcp` integration that uses [Vertex AI](https://cloud.google.com/vertex-ai)
to run your pipelines.

## When to use it

You should use the Vertex orchestrator if:
* ...

## How to deploy it

...

## How to use it

To use the Vertex orchestrator, we need:
* The ZenML `gcp` integration installed. If you haven't done so, run 
    ```shell
    zenml integration install gcp
    ```

We can then register the orchestrator and use it in our active stack:
```shell
zenml orchestrator register <NAME> \
    --flavor=vertex

# Add the orchestrator to the active stack
zenml stack update -o <NAME>
```

TODO: explain how to run a pipeline

A concrete example of using the Vertex orchestrator can be found 
[here](https://github.com/zenml-io/zenml/tree/main/examples/vertex_ai_orchestration).

For more information and a full list of configurable attributes of the Vertex orchestrator, check out the 
[API Docs](https://apidocs.zenml.io/latest/api_docs/integrations/#zenml.integrations.gcp.orchestrators.vertex_orchestrator.VertexOrchestrator).
