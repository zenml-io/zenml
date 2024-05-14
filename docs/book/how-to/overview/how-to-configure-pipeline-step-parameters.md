---
description: >-
  Steps and pipelines can be parameterized just like any other python function
  that you are familiar with.
---

# How to configure pipeline/step parameters

```python
@step
def load_data(parameter: int) -> dict:

    # do something with the parameter here

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


@pipeline  
def simple_ml_pipeline(parameter: int):
    dataset = load_data(parameter=parameter)
    train_model(dataset)
```

{% hint style="info" %}
We recommend strict Typing of all parameters across your pipelines and steps
{% endhint %}
