---
icon: bell-concierge
description: There are numerous ways to trigger a pipeline
---

# Trigger a pipeline

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

![Working with Templates](../../../.gitbook/assets/run-templates.gif)

<table data-view="cards"><thead><tr><th></th><th></th><th></th><th data-hidden data-card-target data-type="content-ref"></th></tr></thead><tbody><tr><td>Use templates: Python SDK</td><td></td><td></td><td><a href="use-templates-python.md">use-templates-python.md</a></td></tr><tr><td>Use templates: CLI</td><td></td><td></td><td><a href="use-templates-cli.md">use-templates-cli.md</a></td></tr><tr><td>Use templates: Dashboard</td><td></td><td></td><td><a href="use-templates-dashboard.md">use-templates-dashboard.md</a></td></tr><tr><td>Use templates: Rest API</td><td></td><td></td><td><a href="use-templates-rest-api.md">use-templates-rest-api.md</a></td></tr></tbody></table>
<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
