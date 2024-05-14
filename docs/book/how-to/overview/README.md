---
description: >-
  Building pipelines is as simple as adding the `@step` and `@pipeline`
  decorators to your code.
---

# Build a pipeline?

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

Check below for more advanced pipelining features.

<table data-view="cards"><thead><tr><th></th><th></th><th></th><th data-hidden data-card-target data-type="content-ref"></th></tr></thead><tbody><tr><td>Configure pipeline/step parameters</td><td></td><td></td><td><a href="how-to-use-pipeline-step-parameters.md">how-to-use-pipeline-step-parameters.md</a></td></tr><tr><td>Control caching behavior</td><td></td><td></td><td><a href="how-to-control-caching-behavior.md">how-to-control-caching-behavior.md</a></td></tr><tr><td>Run pipeline in pipeline</td><td></td><td></td><td><a href="trigger-a-pipeline-from-within-another.md">trigger-a-pipeline-from-within-another.md</a></td></tr></tbody></table>
