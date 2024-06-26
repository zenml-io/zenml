---
description: >-
  Trigger a pipeline from the rest API.
---

# Trigger a pipeline from another

{% hint style="info" %}
This is a [ZenML Pro](https://zenml.io/pro) only feature. Please [sign up here](https://cloud.zenml.io) get access.
OSS users can only trigger a pipeline by calling the pipeline function inside their runner script.
{% endhint %}

Triggering a pipeline from the REST API **only** works with pipelines that are already built with a remote stack
(i.e. at least a remote orchestrator, artifact store, and container registry). Most of the times, this means
you can only *re-run* a pipeline with a remote stack using a different configuration.

As a pre-requisite, you need a pipeline name and version. After you have it, there are three calls that need to be made in order to trigger a pipeline from the REST API:

1. `GET /pipelines?name=<PIPELINE_NAME>&version=<PIPELINE_VERSION>` -> This returns a response, where a <PIPELINE_ID> can be copied
2. `GET /pipeline_builds?pipeline_id=<PIPELINE_ID>` -> This returns a list of responses where a <BUILD_ID> can be chosen
3. `POST /pipeline_builds/<BUILD_ID>/runs` -> This runs the pipeline. You can pass the [PipelineRunConfiguration](https://sdkdocs.zenml.io/latest/core_code_docs/core-config/#zenml.config.pipeline_run_configuration.PipelineRunConfiguration) in the body

The above set of REST calls means that you can only trigger a pipeline that has been [built before](../customize-docker-builds/reuse-docker-builds.md) on a remote stack.

## A worked example

{% hint style="info" %}
Learn how to get a bearer token for the curl commands [here](../../reference/api-reference.md#using-a-bearer-token-to-access-the-api-programatically).
{% endhint %}

Here is an example. Let's say would we like to re-run a pipeline called `training`. We first query the `/pipelines` endpoint:

```shell
curl -X 'GET' \
  '<YOUR_ZENML_SERVER_URL>/api/v1/pipelines?hydrate=false&name=training&version=45' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer <YOUR_TOKEN>'
```

<figure><img src="../../.gitbook/assets/rest_api_step_1.png" alt=""><figcaption><p>Identifying the pipeline ID</p></figcaption></figure>

We can take the ID from any object in the list of responses. In this case, the <PIPELINE_ID> is `c953985e-650a-4cbf-a03a-e49463f58473` in the response.

After this, we take the pipeline ID and call the `/pipeline_builds?pipeline_id=<PIPELINE_ID>` API:

```shell
curl -X 'GET' \
  '<YOUR_ZENML_SERVER_URL>/api/v1/pipeline_builds?hydrate=false&logical_operator=and&page=1&size=20&pipeline_id=b826b714-a9b3-461c-9a6e-1bde3df3241d' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer <YOUR_TOKEN>'
```

We can now take the <BUILD_ID> from this response. Here it is `b826b714-a9b3-461c-9a6e-1bde3df3241d`.

<figure><img src="../../.gitbook/assets/rest_api_step_2.png" alt=""><figcaption><p>Identifying the build ID</p></figcaption></figure>

Finally, we can use the build ID to trigger the pipeline with a different configuration:

```shell
curl -X 'POST' \
  '<YOUR_ZENML_SERVER_URL>/api/v1/pipeline_builds/b826b714-a9b3-461c-9a6e-1bde3df3241d/runs' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer <YOUR_TOKEN>' \
  -d '{
  "steps": {"model_trainer": {"parameters": {"model_type": "rf"}}}
}'
```

A positive response means your pipeline has been re-triggered with a different config!


<table data-view="cards"><thead><tr><th></th><th></th><th></th><th data-hidden data-card-target data-type="content-ref"></th></tr></thead><tbody><tr><td>Learn how to run a pipeline directly from another</td><td></td><td></td><td><a href="trigger-a-pipeline-from-another.md">orchestrators.md</a></td></tr><tr><td>Learn how to run a pipeline directly from the Python client</td><td></td><td></td><td><a href="trigger-a-pipeline-from-client.md">orchestrators.md</a></td></tr></tbody></table>

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>