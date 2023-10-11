---
description: How to orchestrate pipelines with Vertex AI
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


The Vertex orchestrator is an [orchestrator](./orchestrators.md) flavor provided with
the ZenML `gcp` integration that uses [Vertex AI](https://cloud.google.com/vertex-ai)
to run your pipelines.

## When to use it

You should use the Vertex orchestrator if:
* you're already using GCP.
* you're looking for a proven production-grade orchestrator.
* you're looking for a UI in which you can track your pipeline
runs.
* you're looking for a managed solution for running your pipelines.
* you're looking for a serverless solution for running your pipelines.

## How to deploy it

Check out our cloud guide [ZenML Cloud Guide](../../cloud-guide/overview.md)
for information on how to set up the Vertex orchestrator.

## How to use it

To use the Vertex orchestrator, we need:
* The ZenML `gcp` integration installed. If you haven't done so, run 
    ```shell
    zenml integration install gcp
    ```
* [Docker](https://www.docker.com) installed and running.
* [kubectl](https://kubernetes.io/docs/tasks/tools/#kubectl) installed.
* A [remote artifact store](../artifact-stores/artifact-stores.md) as part of your stack.
* A [remote metadata store](../metadata-stores/metadata-stores.md) as part of your stack.
* A [remote container registry](../container-registries/container-registries.md) as part of your stack.
* The GCP project ID and location in which you want to run your Vertex AI pipelines.

We can then register the orchestrator and use it in our active stack:
```shell
zenml orchestrator register <NAME> \
    --flavor=vertex \
    --project=<PROJECT_ID> \
    --location=<GCP_LOCATION>

# Add the orchestrator to the active stack
zenml stack update -o <NAME>
```

{% hint style="info" %}
ZenML will build a Docker image called `zenml-vertex` which includes your code and use it
to run your pipeline steps in Vertex AI. Check out
[this page](../../developer-guide/advanced-usage/docker.md)
if you want to learn more about how ZenML builds these images and
how you can customize them.

If you decide you need the full flexibility of having a
[custom base image](../../developer-guide/advanced-usage/docker.md#using-a-custom-base-image),
you can update your existing orchestrator
```shell
zenml orchestrator update <NAME> \
--custom_docker_base_image_name=<IMAGE_NAME>
```
or set it when registering a new Vertex orchestrator:
```shell
zenml orchestrator register <NAME> \
--flavor=vertex \
--custom_docker_base_image_name=<IMAGE_NAME> \
...
```
{% endhint %}

You can now run any ZenML pipeline using the Vertex orchestrator:
```shell
python file_that_runs_a_zenml_pipeline.py
```

A concrete example of using the Vertex orchestrator can be found 
[here](https://github.com/zenml-io/zenml/tree/main/examples/vertex_ai_orchestration).

For more information and a full list of configurable attributes of the Vertex orchestrator, check out the 
[API Docs](https://apidocs.zenml.io/latest/api_docs/integrations/#zenml.integrations.gcp.orchestrators.vertex_orchestrator.VertexOrchestrator).
