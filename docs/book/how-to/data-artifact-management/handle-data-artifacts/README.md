---
icon: box-archive
description: >-
  Step outputs in ZenML are stored in the artifact store. This enables caching,
  lineage and auditability. Using type annotations helps with transparency, 
  passing data between steps, and serializing/deserializing the data.
---

# Handle Data/Artifacts

For best results, use type annotations for your outputs. This is good coding practice for transparency, helps ZenML handle passing data between steps, and also enables ZenML to serialize and deserialize (referred to as 'materialize' in ZenML) the data.

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

In this code, we define two steps: `load_data` and `train_model`. The `load_data` step takes an integer parameter and returns a dictionary containing training data and labels. The `train_model` step receives the dictionary from `load_data`, extracts the features and labels, and trains a model (not shown here).

Finally, we define a pipeline `simple_ml_pipeline` that chains the `load_data`
and `train_model` steps together. The output from `load_data` is passed as input
to `train_model`, demonstrating how data flows between steps in a ZenML
pipeline.

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
