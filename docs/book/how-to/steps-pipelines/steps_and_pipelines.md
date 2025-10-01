---
description: Steps and Pipelines are the core building blocks of ZenML
icon: arrow-progress
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Steps & Pipelines

Steps and Pipelines are the fundamental building blocks of ZenML. A **Step** is a reusable unit of computation, and a **Pipeline** is a directed acyclic graph (DAG) composed of steps. Together, they allow you to define, version, and execute machine learning workflows.

## The Relationship Between Steps and Pipelines

In ZenML, steps and pipelines work together in a clear hierarchy:

1. **Steps** are individual functions that perform specific tasks, like loading data, processing it, or training models
2. **Pipelines** orchestrate these steps, connecting them in a defined sequence where outputs from one step can flow as inputs to others
3. Each step produces artifacts that are tracked, versioned, and can be reused across pipeline runs

Think of a step as a single LEGO brick, and a pipeline as the complete structure you build by connecting many bricks together.

## Basic Steps

### Creating a Simple Step

A step is created by applying the `@step` decorator to a Python function:

```python
from zenml import step

@step
def load_data() -> dict:
    training_data = [[1, 2], [3, 4], [5, 6]]
    labels = [0, 1, 0]
    return {'features': training_data, 'labels': labels}
```

### Step Inputs and Outputs

Steps can take inputs and produce outputs. These can be simple types, complex data structures, or custom objects.

```python
@step
def process_data(data: dict) -> dict:
    # Input: data dictionary with features and labels
    # Process the input data
    processed_features = [feature * 2 for feature in data['features']]
    
    # Output: return processed data and statistics
    return {
        'processed_features': processed_features,
        'labels': data['labels'],
        'num_samples': len(data['features']),
        'feature_sum': sum(map(sum, data['features']))
    }
```

In this example:

* The step takes a `dict` as input containing features and labels
* It processes the features and computes some statistics
* It returns a new `dict` as output with the processed data and additional information

### Custom Output Names

You can name your step outputs using the `Annotated` type:

```python
from typing import Annotated
from typing import Tuple

@step
def divide(a: int, b: int) -> Tuple[
    Annotated[int, "quotient"],
    Annotated[int, "remainder"]
]:
    return a // b, a % b
```

By default, step outputs are named `output` for single output steps and `output_0`, `output_1`, etc. for steps with multiple outputs.

## Basic Pipelines

### Creating a Simple Pipeline

A pipeline is created by applying the `@pipeline` decorator to a Python function that composes steps together:

```python
from zenml import pipeline

@pipeline
def simple_ml_pipeline():
    dataset = load_data()
    train_model(dataset)
```

### Running Pipelines

You can run a pipeline by simply calling the function:

```python
simple_ml_pipeline()
```

The run is automatically logged to the ZenML dashboard where you can view the DAG and associated metadata.

## End-to-End Example

Here's a simple end-to-end example that demonstrates the basic workflow:

```python
import numpy as np

from typing import Tuple

from zenml import step, pipeline

# Create steps for a simple ML workflow
@step
def get_data() -> Tuple[np.ndarray, np.ndarray]:
    # Generate some synthetic data
    X = np.array([[1, 2], [3, 4], [5, 6], [7, 8]])
    y = np.array([0, 1, 0, 1])
    return X, y

@step
def process_data(data: Tuple[np.ndarray, np.ndarray]) -> Tuple[np.ndarray, np.ndarray]:
    X, y = data
    # Apply a simple transformation
    X_processed = X * 2
    return X_processed, y

@step
def train_and_evaluate(processed_data: Tuple[np.ndarray, np.ndarray]) -> float:
    X, y = processed_data
    # Simplistic "training" - just compute accuracy based on a rule
    predictions = [1 if sum(sample) > 10 else 0 for sample in X]
    accuracy = sum(p == actual for p, actual in zip(predictions, y)) / len(y)
    return accuracy

# Create a pipeline that combines these steps
@pipeline
def simple_example_pipeline():
    raw_data = get_data()
    processed_data = process_data(raw_data)
    accuracy = train_and_evaluate(processed_data)
    print(f"Model accuracy: {accuracy}")

# Run the pipeline
if __name__ == "__main__":
    simple_example_pipeline()
```

## Parameters and Artifacts

### Understanding the Difference

ZenML distinguishes between two types of inputs to steps:

1. **Artifacts**: Outputs from other steps in the same pipeline
   * These are tracked, versioned, and stored in the artifact store
   * They are passed between steps and represent data flowing through your pipeline
   * Examples: datasets, trained models, evaluation metrics
2. **Parameters**: Direct values provided when invoking a step
   * These are typically simple configuration values passed directly to the step
   * They're not tracked as separate artifacts but are recorded with the pipeline run
   * Examples: learning rates, batch sizes, model hyperparameters

This example demonstrates the difference:

```python
@pipeline
def my_pipeline():
    int_artifact = some_other_step()  # This is an artifact
    # input_1 is an artifact, input_2 is a parameter
    my_step(input_1=int_artifact, input_2=42)
```

### Parameter Types

Parameters can be:

1. **Primitive types**: `int`, `float`, `str`, `bool`
2. **Container types**: `list`, `dict`, `tuple` (containing primitives)
3. **Custom types**: As long as they can be serialized to JSON using Pydantic

Parameters that cannot be serialized to JSON should be passed as artifacts rather than parameters.

## Parameterizing Workflows

### Step Parameterization

Steps can take parameters like regular Python functions:

```python
@step
def train_model(data: dict, learning_rate: float = 0.01, epochs: int = 10) -> None:
    # Use learning_rate and epochs parameters
    print(f"Training with learning rate: {learning_rate} for {epochs} epochs")
```

### Pipeline Parameterization

Pipelines can also be parameterized, allowing values to be passed down to steps:

```python
@pipeline
def training_pipeline(dataset_name: str = "default_dataset", learning_rate: float = 0.01):
    data = load_data(dataset_name=dataset_name)
    train_model(data=data, learning_rate=learning_rate, epochs=20)
```

You can then run the pipeline with specific parameters:

```python
training_pipeline(dataset_name="custom_dataset", learning_rate=0.005)
```

## Step Type Handling & Output Management

### Type Annotations

While optional, type annotations are highly recommended and provide several benefits:

* **Artifact handling**: ZenML uses type annotations to determine how to serialize, store, and load [artifacts](../artifacts/artifacts.md). The type information guides ZenML to select the appropriate [materializer](../artifacts/materializers.md) for saving and loading step outputs.
* **Type validation**: ZenML validates inputs against type annotations at runtime to catch errors early.
* **Code documentation**: Types make your code more self-documenting and easier to understand.

```python
from typing import Tuple

@step
def square_root(number: int) -> float:
    return number ** 0.5

@step
def divide(a: int, b: int) -> Tuple[int, int]:
    return a // b, a % b
```

When you specify a return type like `-> float` or `-> Tuple[int, int]`, ZenML uses this information to determine how to store the step's output in the artifact store. For instance, a step returning a pandas DataFrame with the annotation `-> pd.DataFrame` will use the pandas-specific materializer for efficient storage.

{% hint style="info" %}
If you want to enforce type annotations for all steps, set the environment variable `ZENML_ENFORCE_TYPE_ANNOTATIONS` to `True`.
{% endhint %}

### Multiple Return Values

Steps can return multiple artifacts:

```python
from typing import Tuple
from sklearn.base import ClassifierMixin
from typing import Annotated

@step
def train_classifier(X_train, y_train) -> Tuple[
    Annotated[ClassifierMixin, "model"],
    Annotated[float, "accuracy"]
]:
    model = SVC(gamma=0.001)
    model.fit(X_train, y_train)
    accuracy = model.score(X_train, y_train)
    return model, accuracy
```

ZenML uses the following convention to differentiate between a single output of type `Tuple` and multiple outputs:

* When the `return` statement is followed by a tuple literal (e.g., `return 1, 2` or `return (value_1, value_2)`), it's treated as a step with multiple outputs
* All other cases are treated as a step with a single output of type `Tuple`

## Conclusion

Steps and Pipelines provide a flexible, powerful way to build machine learning workflows in ZenML. This guide covered the basic concepts of creating steps and pipelines, managing inputs and outputs, and working with parameters.

For more advanced features, check out the [Advanced Features](advanced_features.md) guide. For configuration using YAML files, see [Configuration with YAML](yaml_configuration.md).
