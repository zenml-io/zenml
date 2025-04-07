---
description: >-
  Learn how ZenML manages data artifacts, tracks versioning and lineage, and
  enables effective data flow between steps.
icon: binary
---

# Artifacts

Artifacts are a cornerstone of ZenML's ML pipeline management system, enabling versioning, lineage tracking, and reproducibility. This guide explains how artifacts work in ZenML and how to use them effectively in your pipelines.

## What Are Artifacts?

In ZenML, artifacts are data objects that:

* Are produced by steps (outputs)
* Are consumed by steps (inputs)
* Are automatically versioned and tracked
* Have their lineage recorded
* Can be stored, retrieved, and visualized

Artifacts are the data that flows between steps in your pipelines, and they form the backbone of ZenML's data management capabilities.

## How Artifacts Work in ZenML

### Basic Artifact Flow

Here's a simple example of how artifacts are created and used in ZenML:

```python
from zenml import pipeline, step
import pandas as pd

@step
def create_data() -> pd.DataFrame:
    """Creates a dataframe that becomes an artifact."""
    return pd.DataFrame({
        "feature_1": [1, 2, 3],
        "feature_2": [4, 5, 6],
        "target": [10, 20, 30]
    })

@step
def process_data(df: pd.DataFrame) -> pd.DataFrame:
    """Takes an artifact as input and returns a new artifact."""
    df["feature_3"] = df["feature_1"] * df["feature_2"]
    return df

@pipeline
def simple_pipeline():
    """Pipeline that creates and processes artifacts."""
    data = create_data()  # Produces an artifact
    processed_data = process_data(data)  # Uses and produces artifacts

# Run the pipeline
simple_pipeline()
```

When this pipeline runs:

1. `create_data()` executes and returns a DataFrame
2. ZenML saves this DataFrame as an artifact in the artifact store
3. `process_data()` receives this artifact as an input
4. `process_data()` returns a new DataFrame, which becomes another artifact

### How ZenML Stores Artifacts

When a step produces an output, ZenML:

1. Creates a unique directory in the artifact store
2. Uses a materializer to serialize the data
3. Stores the serialized data in that directory
4. Records metadata about the artifact
5. Returns a reference to the artifact

Each pipeline run generates a new set of artifacts, which are organized in the artifact store like this:

```
artifacts/
├── 2023-06-15/
│   ├── 34a2c1f5-7dfa-4b9e-8e5c-6c7b2d3a1e8f/  # Artifact directory
│   │   ├── data/  # Serialized data
│   │   └── metadata.json  # Metadata about the artifact
│   └── b9e8c5f4-3a1e-7dfa-2d3a-6c7b4b9e8e5c/  # Another artifact
└── 2023-06-16/
    └── ...
```

### Materializers: How Data Gets Stored

Materializers are a key concept in ZenML's artifact system. They handle:

* **Serializing data** when saving artifacts to storage
* **Deserializing data** when loading artifacts from storage
* **Generating visualizations** for the dashboard
* **Extracting metadata** for tracking and searching

When a step produces an output, ZenML automatically selects the appropriate materializer based on the data type (using type annotations). ZenML includes built-in materializers for common data types like:

* Primitive types (`int`, `float`, `str`, `bool`)
* Container types (`dict`, `list`, `tuple`)
* NumPy arrays
* Pandas DataFrames
* Many ML model formats (through integrations)

Here's how materializers work in practice:

```python
@step
def train_model(X_train, y_train) -> sklearn.linear_model.LinearRegression:
    """Train a model and return it as an artifact."""
    model = LinearRegression()
    model.fit(X_train, y_train)
    return model  # ZenML uses a specific materializer for scikit-learn models
```

For custom data types, you can create your own materializers. See the [Materializers](materializers.md) guide for details.

### Lineage and Caching

ZenML automatically tracks the complete lineage of each artifact:

* Which step produced it
* Which pipeline run it belongs to
* Which other artifacts it depends on
* Which steps have consumed it

This lineage tracking enables powerful caching capabilities. When you run a pipeline, ZenML checks if any steps have been run before with the same inputs, code, and configuration. If so, it reuses the cached outputs instead of rerunning the step:

```python
@pipeline
def cached_pipeline():
    # If create_data has been run before with the same code and inputs,
    # the cached artifact will be used
    data = create_data()
    
    # If process_data has been run before with the same code and inputs
    # (including the exact same data artifact), the cached output will be used
    processed_data = process_data(data)
```

## Working with Artifacts

### Type Annotations and Artifact Handling

Type annotations are crucial when working with artifacts as they:

1. Help ZenML select the appropriate materializer
2. Validate inputs and outputs
3. Document the data flow of your pipeline

```python
from typing import Tuple, List
import numpy as np

@step
def preprocess_data(df: pd.DataFrame) -> np.ndarray:
    """Type annotation tells ZenML this returns a numpy array."""
    return df.values

@step
def split_data(data: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Type annotation tells ZenML this returns a tuple of numpy arrays."""
    split_point = len(data) // 2
    return data[:split_point], data[split_point:]
```

When you specify a return type like `-> np.ndarray`, ZenML uses this information to select the appropriate materializer. The more specific your type annotations, the better ZenML can handle your data.

### Naming Your Artifacts

By default, artifacts are named based on their position or variable name:

* Single outputs are named `output`
* Multiple outputs are named `output_0`, `output_1`, etc.

You can give your artifacts more meaningful names using the `Annotated` type:

```python
from typing import Tuple
from typing_extensions import Annotated  # or `from typing import Annotated` in Python 3.9+

@step
def split_dataset(
    df: pd.DataFrame
) -> Tuple[
    Annotated[pd.DataFrame, "train_data"],
    Annotated[pd.DataFrame, "test_data"]
]:
    """Split a dataframe into training and testing sets."""
    train = df.sample(frac=0.8, random_state=42)
    test = df.drop(train.index)
    return train, test
```

You can even use dynamic naming with placeholders:

```python
@step
def extract_data(source: str) -> Annotated[pd.DataFrame, "{dataset_type}_data"]:
    """Extract data with a dynamically named output."""
    # Implementation...
    return data

@pipeline
def data_pipeline():
    # These will create artifacts named "train_data" and "test_data"
    train_df = extract_data.with_options(
        substitutions={"dataset_type": "train"}
    )(source="train_source")
    
    test_df = extract_data.with_options(
        substitutions={"dataset_type": "test"}
    )(source="test_source")
```

ZenML supports these placeholders:

* `{date}`: Current date (e.g., "2023\_06\_15")
* `{time}`: Current time (e.g., "14\_30\_45\_123456")
* Custom placeholders can be defined using `substitutions`

### Returning Multiple Outputs

Steps can return multiple artifacts using tuples:

```python
from typing import Tuple, Annotated
import numpy as np

@step
def split_data(
    data: np.ndarray, 
    target: np.ndarray
) -> Tuple[
    Annotated[np.ndarray, "X_train"],
    Annotated[np.ndarray, "X_test"],
    Annotated[np.ndarray, "y_train"],
    Annotated[np.ndarray, "y_test"]
]:
    """Split data into training and testing sets."""
    # Implement split logic
    X_train, X_test = data[:80], data[80:]
    y_train, y_test = target[:80], target[80:]
    
    return X_train, X_test, y_train, y_test
```

ZenML differentiates between:

* A step with multiple outputs: `return a, b` or `return (a, b)`
* A step with a single tuple output: `return some_tuple`

### Accessing Artifacts

You can access artifacts from past runs using the ZenML Client:

```python
from zenml.client import Client

# Get a specific run
client = Client()
pipeline_run = client.get_pipeline_run("<PIPELINE_RUN_ID>")

# Get an artifact from a specific step
step = pipeline_run.steps["split_data"]
X_train = step.outputs["X_train"].load()

# Use the artifact
print(X_train.shape)
```

You can also access artifacts by name and version:

```python
# Get a specific artifact version
artifact = client.get_artifact_version("my_model", "1.0")

# Get the latest version of an artifact
latest_artifact = client.get_artifact_version("my_model")

# Load it into memory
model = latest_artifact.load()
```

### Accessing Artifacts in Steps

You can access any artifact within a step, not just those passed as inputs:

```python
from zenml.client import Client
from zenml import step

@step
def evaluate_against_previous(model, X_test, y_test) -> float:
    """Compare current model with the previous best model."""
    client = Client()
    
    # Get the previous best model
    best_model = client.get_artifact_version("best_model")
    
    # Use it for comparison
    previous_accuracy = best_model.data.score(X_test, y_test)
    current_accuracy = model.score(X_test, y_test)
    
    return current_accuracy - previous_accuracy
```

### Artifact vs. Parameter Inputs

When calling a step, inputs can be either:

* **Artifacts**: Outputs from other steps, tracked and versioned by ZenML
* **Parameters**: Literal values provided directly to the step

```python
@pipeline
def training_pipeline():
    # data is an artifact
    data = load_data()
    
    # data is an artifact, learning_rate is a parameter
    model = train_model(data=data, learning_rate=0.01)
```

Parameters are limited to JSON-serializable values (numbers, strings, lists, dictionaries, etc.). More complex objects should be passed as artifacts.

## Advanced Artifact Usage

### Visualizing Artifacts

ZenML automatically generates visualizations for many types of artifacts, viewable in the dashboard:

```python
# You can also view visualizations in notebooks
from zenml.client import Client

artifact = Client().get_artifact_version("<ARTIFACT_NAME>")
artifact.visualize()
```

For detailed information on visualizations, see [Visualizations](visualizations.md).

### Deleting Artifacts

Individual artifacts cannot be deleted directly (to prevent broken references). However, you can clean up unused artifacts:

```bash
zenml artifact prune
```

This deletes artifacts that are no longer referenced by any pipeline run. You can control this behavior with flags:

* `--only-artifact`: Only delete the physical files, keep database entries
* `--only-metadata`: Only delete database entries, keep files
* `--ignore-errors`: Continue pruning even if some artifacts can't be deleted

### Exchanging Artifacts Between Pipelines

You can use artifacts produced by one pipeline in another pipeline:

```python
from zenml.client import Client
from zenml import step, pipeline

@step
def use_trained_model(data: pd.DataFrame, model) -> pd.Series:
    """Use a model loaded from a previous pipeline run."""
    return pd.Series(model.predict(data))

@pipeline
def inference_pipeline():
    # Load data
    data = load_data()
    
    # Get the latest model from another pipeline
    model = Client().get_artifact_version("trained_model")
    
    # Use it for predictions
    predictions = use_trained_model(data=data, model=model)
```

This allows you to build modular pipelines that can work together as part of a larger ML system.

## Conclusion

Artifacts are a central part of ZenML's approach to ML pipelines. They provide:

* Automatic versioning and lineage tracking
* Efficient storage and caching
* Type-safe data handling
* Visualization capabilities
* Cross-pipeline data sharing

By understanding how artifacts work, you can build more effective, maintainable, and reproducible ML pipelines.

For more information on specific aspects of artifacts, see:

* [Materializers](materializers.md): Creating custom serializers for your data types
* [Visualizations](visualizations.md): Customizing artifact visualizations
