---
description: >-
  Step outputs in ZenML are stored in the artifact store. This enables caching,
  lineage and auditability.
---

# 🪅 Handle Data/Artifacts

For best results, use type annotations for your outputs.

```python
@step
def load_data(parameter: int) -> Dict[str, Any]:

    # do something with the parameter here

    training_data = [[1, 2], [3, 4], [5, 6]]
    labels = [0, 1, 0]
    return {'features': training_data, 'labels': labels}

@step
def train_model(data: Dict[str, Any]) -> None:
    total_features = sum(map(sum, data['features']))
    total_labels = sum(data['labels'])
    
    # Train some model here
    
    print(f"Trained model using {len(data['features'])} data points. "
          f"Feature sum is {total_features}, label sum is {total_labels}")


@pipeline  
def simple_ml_pipeline(parameter: int):
    dataset = load_data(parameter=parameter)  # Get the output 
    train_model(dataset)  # Pipe the previous step output into the downstream step
```
