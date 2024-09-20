---
description: There are numerous ways to trigger a pipeline
---

In ZenML, the simplest way to execute a run is to use your pipeline function:

```python
from zenml import step, pipeline


@step  # Just add this decorator
def load_data() -> dict:
    training_data = [[1, 2], [3, 4], [5, 6]]
    labels = [0, 1, 0]
    return {'features': training_data, 'labels': labels}


@step
def train_model(data: dict) -> None:
    total_features = sum(map(sum, data['features']))
    total_labels = sum(data['labels'])

    # Train some model here...

    print(
        f"Trained model using {len(data['features'])} data points. "
        f"Feature sum is {total_features}, label sum is {total_labels}."
    )


@pipeline  # This function combines steps together 
def simple_ml_pipeline():
    dataset = load_data()
    train_model(dataset)


if __name__ == "__main__":
    simple_ml_pipeline()
```

However, there are other ways to trigger a pipeline, specifically a pipeline 
with a remote stack (remote orchestrator, artifact store, and container 
registry).

## Run Templates

**Run Templates** are pre-defined, parameterized configurations for your ZenML 
pipelines that can be easily executed from the ZenML dashboard or via our 
Client/REST API. Think of them as blueprints for your pipeline runs, ready 
to be customized on the fly.

{% hint style="success" %}
This is a [ZenML Pro](https://zenml.io/pro)-only feature. Please
[sign up here](https://cloud.zenml.io) to get access.
{% endhint %}

![Run Template](../../.gitbook/assets/run-templates.gif)

{% hint style="warning" %}
It is important to note that in order to create a run template, you will 
need **a pipeline run that was executed on a remote stack** (i.e. at least a 
remote orchestrator, artifact store, and container registry).
{% endhint %}

<table data-view="cards"><thead><tr><th></th><th></th><th></th><th data-hidden data-card-target data-type="content-ref"></th></tr></thead><tbody><tr><td>Trigger a pipeline from Python SDK</td><td></td><td></td><td><a href="trigger-a-pipeline-from-client.md">trigger-a-pipeline-from-client.md</a></td></tr><tr><td>Trigger a pipeline from another</td><td></td><td></td><td><a href="trigger-a-pipeline-from-another.md">trigger-a-pipeline-from-another.md</a></td></tr><tr><td>Trigger a pipeline from the REST API</td><td></td><td></td><td><a href="trigger-a-pipeline-from-rest-api.md">trigger-a-pipeline-from-rest-api.md</a></td></tr></tbody></table>

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
