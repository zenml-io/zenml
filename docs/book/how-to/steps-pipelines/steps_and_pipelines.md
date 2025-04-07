---
description: Steps and Pipelines are the core building blocks of ZenML
icon: arrow-progress
---

# Steps & Pipelines

Steps and Pipelines are the fundamental building blocks of ZenML. A **Step** is a reusable unit of computation, and a **Pipeline** is a directed acyclic graph (DAG) composed of steps. Together, they allow you to define, version, and execute machine learning workflows.

## Creating Steps

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
def train_model(data: dict) -> None:
    total_features = sum(map(sum, data['features']))
    total_labels = sum(data['labels'])
    print(f"Trained model using {len(data['features'])} data points. "
          f"Feature sum is {total_features}, label sum is {total_labels}")
```

### Type Annotations

While optional, type annotations are highly recommended and provide several benefits:

* **Artifact handling**: ZenML uses type annotations to determine how to serialize, store, and load artifacts. The type information guides ZenML to select the appropriate materializer for saving and loading step outputs.
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

If you want to enforce type annotations for all steps, set the environment variable `ZENML_ENFORCE_TYPE_ANNOTATIONS` to `True`.

### Custom Output Names

You can name your step outputs using the `Annotated` type:

```python
from typing_extensions import Annotated  # or `from typing import Annotated` on Python 3.9+
from typing import Tuple

@step
def divide(a: int, b: int) -> Tuple[
    Annotated[int, "quotient"],
    Annotated[int, "remainder"]
]:
    return a // b, a % b
```

By default, step outputs are named `output` for single output steps and `output_0`, `output_1`, etc. for steps with multiple outputs.

### Multiple Return Values

Steps can return multiple artifacts:

```python
from typing import Tuple
from sklearn.base import ClassifierMixin
from typing_extensions import Annotated

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

## Creating Pipelines

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

## Pipeline and Step Parameters

When calling a step in a pipeline, inputs can be either:

* **Artifacts**: Outputs from other steps in the same pipeline. These are tracked, versioned, and stored in the artifact store.
* **Parameters**: Values provided explicitly when invoking a step. These are typically simple values that are directly passed to the step function.

```python
@pipeline
def my_pipeline():
    int_artifact = some_other_step()  # This is an artifact
    # input_1 is an artifact, input_2 is a parameter
    my_step(input_1=int_artifact, input_2=42)
```

In this example:

* `input_1` is an artifact because it comes from another step
* `input_2` is a parameter because it's a literal value (42) provided directly

Artifacts are automatically tracked and versioned by ZenML, while parameters are simply passed through to the step function. This distinction affects how you should design your steps and what types of values you can use.

### Parameter Types

Now that we understand the difference between artifacts and parameters, let's look at what types of values can be used as parameters:

1. **Primitive types**: `int`, `float`, `str`, `bool`
2. **Container types**: `list`, `dict`, `tuple` (containing primitives)
3. **Custom types**: As long as they can be serialized to JSON using Pydantic

Parameters that cannot be serialized to JSON should be passed as artifacts rather than parameters.

### Parameterizing Steps and Pipelines

Both pipelines and steps can be parameterized like regular Python functions:

```python
@step
def train_model(data: dict, learning_rate: float = 0.01, epochs: int = 10) -> None:
    # Use learning_rate and epochs parameters
    print(f"Training with learning rate: {learning_rate} for {epochs} epochs")

@pipeline
def training_pipeline(dataset_name: str = "default_dataset"):
    data = load_data(dataset_name=dataset_name)
    train_model(data=data, learning_rate=0.005, epochs=20)
```

You can then run the pipeline with specific parameters:

```python
training_pipeline(dataset_name="custom_dataset")
```

### Passing Between Steps

You can pass parameters to a step in several ways:

**Via Artifacts**

```python
@step
def generate_params() -> dict:
    return {"learning_rate": 0.01, "epochs": 10}

@step
def train_model(params: dict):
    learning_rate = params["learning_rate"]
    epochs = params["epochs"]
    # Use parameters
```

**Via Pipeline Parameters**

```python
@pipeline
def training_pipeline(learning_rate: float):
    data = load_data()
    train_model(data=data, learning_rate=learning_rate)
```

## Conclusion

Steps and Pipelines provide a flexible, powerful way to build machine learning workflows in ZenML. This guide covered the basic concepts of creating steps and pipelines, managing inputs and outputs, and working with parameters.

For more advanced features, check out the [Advanced Features](advanced_features.md) guide. For configuration using YAML files, see [Configuration with YAML](configuration_with_yaml.md).
