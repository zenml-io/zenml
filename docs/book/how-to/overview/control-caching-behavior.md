---
description: >-
  By default steps in ZenML pipelines are cached whenever code and parameters
  stay unchanged.
---

# How to control caching behavior

```python
@step(enable_cache=True) # set cache behavior at step level
def load_data(parameter: int) -> dict:
    training_data = [[1, 2], [3, 4], [5, 6]]
    labels = [0, 1, 0]
    return {'features': training_data, 'labels': labels}

@step(enable_cache=False) # settings at step level override pipeline level
def train_model(data: dict) -> None:
    total_features = sum(map(sum, data['features']))
    total_labels = sum(data['labels'])
    
    print(f"Trained model using {len(data['features'])} data points. "
          f"Feature sum is {total_features}, label sum is {total_labels}")


@pipeline(enable_cache=True) # set cache behavior at step level
def simple_ml_pipeline(parameter: int):
    dataset = load_data(parameter=parameter)
    train_model(dataset)
```

{% hint style="info" %}
Caching only happens when code and parameters stay the same.
{% endhint %}
