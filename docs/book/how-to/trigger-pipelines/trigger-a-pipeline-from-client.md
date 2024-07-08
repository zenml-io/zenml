---
description: >-
  Trigger a pipeline using the ZenML Client.
---

# Trigger a pipeline from the Python Client

{% hint style="info" %}
This is a [ZenML Pro](https://zenml.io/pro) only feature. Please [sign up here](https://cloud.zenml.io) get access.
OSS users can only trigger a pipeline by calling the pipeline function inside their runner script.
{% endhint %}

Triggering a pipeline from the Python client **only** works with pipelines that are configured with a remote stack
(i.e. at least a remote orchestrator, artifact store, and container registry)

```python
from zenml.client import Client
from zenml.config.pipeline_run_configuration import PipelineRunConfiguration

if __name__ == "__main__":
    run_config = PipelineRunConfiguration(steps={"trainer": {"parameters": {"data_artifact_id": data_artifact_id}}})
    Client().trigger_pipeline("training_pipeline", run_configuration=run_config)
```

{% hint style="info" %}
The pipeline that you're triggering (i.e. `training_pipeline` in the above example) has to have been run previously on a remote stack. In other words, the functionality to trigger a pipeline from another only works when a Docker image has previously been built for that pipeline. In most cases this will be because you ran the pipeline already, but in some cases you might have built the image separately.
{% endhint %}

Read more about the [PipelineRunConfiguration](https://sdkdocs.zenml.io/latest/core_code_docs/core-config/#zenml.config.pipeline_run_configuration.PipelineRunConfiguration) object in the [SDK Docs](https://sdkdocs.zenml.io/).

<table data-view="cards"><thead><tr><th></th><th></th><th></th><th data-hidden data-card-target data-type="content-ref"></th></tr></thead><tbody><tr><td>Learn how to run a pipeline directly from another</td><td></td><td></td><td><a href="trigger-a-pipeline-from-another.md">orchestrators.md</a></td></tr><tr><td>Learn how to run a pipeline from the REST API</td><td></td><td></td><td><a href="trigger-a-pipeline-from-rest-api.md">orchestrators.md</a></td></tr></tbody></table>

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
