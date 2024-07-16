---
description: >-
  Trigger a pipeline from another pipeline.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Trigger a pipeline from another pipeline

{% hint style="info" %}
This is a [ZenML Pro](https://zenml.io/pro) only feature. Please [sign up here](https://cloud.zenml.io) get access.
OSS users can only trigger a pipeline by calling the pipeline function inside their runner script.
{% endhint %}

Triggering a pipeline from another **only** works with pipelines that are configured with a remote stack
(i.e. at least a remote orchestrator, artifact store, and container registry). In order to trigger a pipeline
from another, you can simply use the same syntax as you would if you wanted to trigger a pipeline from the
[Client directly](trigger-a-pipeline-from-client.md).

```python
import pandas as pd
from zenml import pipeline, step
from zenml.client import Client
from zenml.config.pipeline_run_configuration import PipelineRunConfiguration

@step  
def trainer(data_artifact_id: str):
    df = load_artifact(data_artifact_id)

@pipeline
def training_pipeline():
    trainer()

@step  
def load_data() -> pd.Dataframe:
    ...

@step  
def trigger_pipeline(df: UnmaterializedArtifact):
    # By using UnmaterializedArtifact we can get the ID of the artifact
    run_config = PipelineRunConfiguration(steps={"trainer": {"parameters": {"data_artifact_id": df.id}}})
    Client().trigger_pipeline("training_pipeline", run_configuration=run_config)

@pipeline  
def loads_data_and_triggers_training():
    df = load_data()
    trigger_pipeline(df)  # Will trigger the other pipeline
```

{% hint style="info" %}
The pipeline that you're triggering (i.e. `training_pipeline` in the above example) has to have been run previously on a remote stack. In other words, the functionality to trigger a pipeline from another only works when a Docker image has previously been built for that pipeline. In most cases this will be because you ran the pipeline already, but in some cases you might have built the image separately.
{% endhint %}

Read more about the [PipelineRunConfiguration](https://sdkdocs.zenml.io/latest/core_code_docs/core-config/#zenml.config.pipeline_run_configuration.PipelineRunConfiguration) and [`trigger_pipeline`](https://sdkdocs.zenml.io/0.60.0/core_code_docs/core-client/#zenml.client.Client) function object in the [SDK Docs](https://sdkdocs.zenml.io/).

Read more about Unmaterialized Artifacts [here](../handle-data-artifacts/unmaterialized-artifacts.md).

<table data-view="cards"><thead><tr><th></th><th></th><th></th><th data-hidden data-card-target data-type="content-ref"></th></tr></thead><tbody><tr><td>Learn how to run a pipeline directly from the Python Client</td><td></td><td></td><td><a href="trigger-a-pipeline-from-client.md">orchestrators.md</a></td></tr><tr><td>Learn how to run a pipeline from the REST API</td><td></td><td></td><td><a href="trigger-a-pipeline-from-rest-api.md">orchestrators.md</a></td></tr></tbody></table>

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
