---
description: >-
  Trigger a pipeline from the rest API.
---

# Trigger a pipeline from another

{% hint style="info" %}
This is a [ZenML Pro](https://zenml.io/pro) only feature. Please [sign up here](https://cloud.zenml.io) get access.
OSS users can only trigger a pipeline by calling the pipeline function inside their runner script.
{% endhint %}

Triggering a pipeline from the REST API **only** works with pipelines that are configured with a remote stack
(i.e. at least a remote orchestrator, artifact store, and container registry)

There are three calls that need to be made in order to trigger a pipeline from the REST API:

1. `GET /pipelines?name=<PIPELINE_NAME>` -> This returns the <PIPELINE_ID>
2. `GET /pipeline_builds?pipeline_id=<PIPELINE_ID>` -> This returns the build ID
3. `POST /pipeline_builds/<BUILD_ID>/runs` -> This runs the pipeline. You can pass the [PipelineRunConfiguration](https://sdkdocs.zenml.io/latest/core_code_docs/core-config/#zenml.config.pipeline_run_configuration.PipelineRunConfiguration) in the body

The above set of REST calls means that you can only trigger a pipeline that has been [built before](../customize-docker-builds/reuse-docker-builds.md).

<table data-view="cards"><thead><tr><th></th><th></th><th></th><th data-hidden data-card-target data-type="content-ref"></th></tr></thead><tbody><tr><td>Learn how to run a pipeline directly from another</td><td></td><td></td><td><a href="trigger-a-pipeline-from-another.md">orchestrators.md</a></td></tr><tr><td>Learn how to run a pipeline directly from the Python client</td><td></td><td></td><td><a href="trigger-a-pipeline-from-client.md">orchestrators.md</a></td></tr></tbody></table>

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>