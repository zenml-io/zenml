---
description: >-
  There are numerous ways to trigger a pipeline, apart from
  calling the runner script.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# 🚨 Trigger a pipeline

A pipeline can be run via Python like this:

```python
@step  # Just add this decorator
def load_data() -> dict:
    training_data = [[1, 2], [3, 4], [5, 6]]
    labels = [0, 1, 0]
    return {'features': training_data, 'labels': labels}


@step
def train_model(data: dict) -> None:
    total_features = sum(map(sum, data['features']))
    total_labels = sum(data['labels'])

    # Train some model here

    print(f"Trained model using {len(data['features'])} data points. "
          f"Feature sum is {total_features}, label sum is {total_labels}")


@pipeline  # This function combines steps together 
def simple_ml_pipeline():
    dataset = load_data()
    train_model(dataset)
```

You can now run this pipeline by simply calling the function:

```python
simple_ml_pipeline()
```

However, there are other ways to trigger a pipeline, specifically a pipeline with a remote stack (remote
orchestrator, artifact store, and container registry).

<table data-view="cards"><thead><tr><th></th><th></th><th></th><th data-hidden data-card-target data-type="content-ref"></th></tr></thead><tbody><tr><td>Trigger a pipeline from Python SDK</td><td></td><td></td><td><a href="trigger-a-pipeline-from-client.md">trigger-a-pipeline-from-client.md</a></td></tr><tr><td>Trigger a pipeline from another</td><td></td><td></td><td><a href="trigger-a-pipeline-from-another.md">trigger-a-pipeline-from-another.md</a></td></tr><tr><td>Trigger a pipeline from the REST API</td><td></td><td></td><td><a href="trigger-a-pipeline-from-rest-api.md">trigger-a-pipeline-from-rest-api.md</a></td></tr></tbody></table>

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
