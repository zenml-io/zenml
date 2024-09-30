---
description: Reuse steps between pipelines.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Compose pipelines

Sometimes it can be useful to extract some common functionality into separate functions
in order to avoid code duplication. To facilitate this, ZenML allows you to compose your pipelines:

```python
from zenml import pipeline

@pipeline
def data_loading_pipeline(mode: str):
    if mode == "train":
        data = training_data_loader_step()
    else:
        data = test_data_loader_step()
    
    processed_data = preprocessing_step(data)
    return processed_data


@pipeline
def training_pipeline():
    training_data = data_loading_pipeline(mode="train")
    model = training_step(data=training_data)
    test_data = data_loading_pipeline(mode="test")
    evaluation_step(model=model, data=test_data)
```

{% hint style="info" %}
Here we are calling one pipeline from within another pipeline, so functionally the `data_loading_pipeline` is functioning as a step within the `training_pipeline`, i.e. the steps of the former are added to the latter. Only the parent pipeline will be visible in the dashboard. In order to actually trigger a pipeline from another, see [here](../trigger-pipelines/trigger-a-pipeline-from-another.md)
{% endhint %}

<table data-view="cards"><thead><tr><th></th><th></th><th></th><th data-hidden data-card-target data-type="content-ref"></th></tr></thead><tbody><tr><td>Learn more about orchestrators here</td><td></td><td></td><td><a href="../../component-guide/orchestrators/orchestrators.md">orchestrators.md</a></td></tr></tbody></table>

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>