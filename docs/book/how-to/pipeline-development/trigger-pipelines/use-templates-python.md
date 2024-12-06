---
description: Create and run a template using the ZenML Python SDK
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


{% hint style="success" %}
This is a [ZenML Pro](https://zenml.io/pro)-only feature. Please
[sign up here](https://cloud.zenml.io) to get access.
{% endhint %}

## Create a template

You can use the ZenML client to create a run template:

```python
from zenml.client import Client

run = Client().get_pipeline_run(<RUN_NAME_OR_ID>)

Client().create_run_template(
    name=<TEMPLATE_NAME>,
    deployment_id=run.deployment_id
)
```

{% hint style="warning" %}
You need to select **a pipeline run that was executed on a remote stack** 
(i.e. at least a remote orchestrator, artifact store, and container registry)
{% endhint %}


You can also create a template directly from your pipeline definition by running the
following code while having a **remote stack** active:
```python
from zenml import pipeline

@pipeline
def my_pipeline():
    ...

template = my_pipeline.create_run_template(name=<TEMPLATE_NAME>)
```

## Run a template 

You can use the ZenML client to run a template:

```python
from zenml.client import Client

template = Client().get_run_template(<TEMPLATE_NAME>)

config = template.config_template

# [OPTIONAL] ---- modify the config here ----

Client().trigger_pipeline(
    template_id=template.id,
    run_configuration=config,
)
```

Once you trigger the template, a new run will be executed on the same stack as 
the original run was executed on.

## Advanced Usage: Run a template from another pipeline

It is also possible to use the same logic to run a pipeline within another 
pipeline:

```python
import pandas as pd

from zenml import pipeline, step
from zenml.artifacts.unmaterialized_artifact import UnmaterializedArtifact
from zenml.artifacts.utils import load_artifact
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
    run_config = PipelineRunConfiguration(
        steps={"trainer": {"parameters": {"data_artifact_id": df.id}}}
    )

    Client().trigger_pipeline("training_pipeline", run_configuration=run_config)


@pipeline
def loads_data_and_triggers_training():
    df = load_data()
    trigger_pipeline(df)  # Will trigger the other pipeline
```

Read more about the [PipelineRunConfiguration](https://sdkdocs.zenml.io/latest/core_code_docs/core-config/#zenml.config.pipeline_run_configuration.PipelineRunConfiguration) and [`trigger_pipeline`](https://sdkdocs.zenml.io/latest/core_code_docs/core-client/#zenml.client.Client) function object in the [SDK Docs](https://sdkdocs.zenml.io/).

Read more about Unmaterialized Artifacts [here](../../data-artifact-management/handle-data-artifacts/unmaterialized-artifacts.md).

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>

