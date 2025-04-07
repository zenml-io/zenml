---
description: >-
  Learn how ZenML manages data artifacts, tracks versioning and lineage, and enables effective data flow between steps.
---

# Artifacts in ZenML

Artifacts are a cornerstone of ZenML's ML pipeline management, enabling versioning, lineage tracking, and reproducibility. This guide explains how artifacts work and how to use them effectively in your pipelines.

## Introduction to Artifacts

In ZenML, artifacts are data objects produced and consumed by pipeline steps. They are automatically:

- **Versioned**: Every artifact is uniquely identified and tracked
- **Stored**: Artifacts are saved to a configured artifact store
- **Cached**: Artifacts enable caching of step outputs
- **Tracked**: Their lineage and relationships are recorded
- **Typed**: Type annotations help validate and document data flows

Artifacts are essential for creating reproducible, traceable ML workflows where every data component is identifiable and accessible.

## Understanding Artifacts

### What Are Artifacts?

At its core, an artifact is any data object that:

- Is returned by a step function
- Is passed as an input to a step function
- Is uniquely identified and versioned
- Can be stored and retrieved
- Has its lineage tracked

Here's a simple example of how artifacts are created in ZenML:

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
    data = create_data()
    processed_data = process_data(data)

# Run the pipeline
simple_pipeline()
```

In this example:
1. `create_data()` produces a DataFrame artifact
2. The artifact is passed to `process_data()`
3. `process_data()` returns a new artifact

### Materializers: The Core of Artifact Handling

One of the most important concepts in ZenML's artifact system is the **materializer**. Materializers are responsible for:

- **Serializing** data when saving artifacts to storage
- **Deserializing** data when loading artifacts from storage
- **Generating visualizations** for artifacts in the dashboard
- **Extracting metadata** for tracking and searching

ZenML includes built-in materializers for common data types like:
- Primitive types (`int`, `float`, `str`, `bool`)
- Container types (`dict`, `list`, `tuple`)
- NumPy arrays
- Pandas DataFrames
- Various ML model formats

When a step produces an output, ZenML automatically:
1. Identifies the appropriate materializer based on the data type (using type annotations)
2. Uses that materializer to save the data to the artifact store
3. Records metadata about the artifact

Here's how this works in practice:

```python
@step
def create_model() -> sklearn.linear_model.LinearRegression:
    """Creates a model that becomes an artifact."""
    model = LinearRegression()
    model.fit(X_train, y_train)
    return model  # ZenML uses an appropriate materializer for scikit-learn models
```

For custom data types, you can create your own materializers. See the [Materializers](./materializers.md) guide for details.

### Artifact Storage Mechanism

ZenML handles artifact storage through this process:

1. When a step produces an output, ZenML:
   - Creates a unique directory in the artifact store
   - Uses a materializer to serialize the data
   - Stores metadata about the artifact
   - Returns a reference to the artifact

2. When a step needs an input, ZenML:
   - Locates the artifact in the store
   - Deserializes it using the appropriate materializer
   - Provides it to the step function

Here's how this works behind the scenes:

```
# Example Artifact Store Structure
artifacts/
├── 2023-06-15/
│   ├── 34a2c1f5-7dfa-4b9e-8e5c-6c7b2d3a1e8f/  # Artifact directory
│   │   ├── data/  # Serialized data
│   │   └── metadata.json  # Metadata about the artifact
│   └── b9e8c5f4-3a1e-7dfa-2d3a-6c7b4b9e8e5c/  # Another artifact
└── 2023-06-16/
    └── ...
```

### Lineage and Caching

ZenML tracks the complete lineage of each artifact:

- Which step produced it
- Which pipeline run it belongs to
- Which other artifacts it depends on
- Which steps have consumed it

This lineage tracking enables powerful caching capabilities:

```python
@pipeline
def cached_pipeline():
    """Pipeline that benefits from caching."""
    # If this step has been run before with the same
    # inputs and code, the cached artifact will be used
    data = create_data()
    # If inputs or code change, the step is rerun
    processed_data = process_data(data)
```

## Working with Artifacts

### Type Annotations

Type annotations are crucial when working with artifacts as they:

1. Help ZenML select the appropriate materializer
2. Validate inputs and outputs
3. Document the data flow of your pipeline
4. Improve IDE and static analysis support

```python
from typing import List, Dict, Tuple, Annotated
import numpy as np

@step
def split_data(
    df: pd.DataFrame
) -> Tuple[
    Annotated[np.ndarray, "X_train"],
    Annotated[np.ndarray, "X_test"],
    Annotated[np.ndarray, "y_train"],
    Annotated[np.ndarray, "y_test"]
]:
    """Split data into training and testing sets with annotations."""
    X = df.drop("target", axis=1).values
    y = df["target"].values
    
    # Split data 80/20
    train_size = int(0.8 * len(X))
    X_train, X_test = X[:train_size], X[train_size:]
    y_train, y_test = y[:train_size], y[train_size:]
    
    return X_train, X_test, y_train, y_test
```

### Returning Multiple Outputs

Steps can return multiple artifacts using tuples or other collection types:

```python
from typing import Tuple, Annotated

@step
def clean_data(
    df: pd.DataFrame
) -> Tuple[
    Annotated[pd.DataFrame, "x_train"],
    Annotated[pd.DataFrame, "x_test"],
    Annotated[pd.Series, "y_train"],
    Annotated[pd.Series, "y_test"]
]:
    """Clean data and split it into training and testing sets."""
    # Data cleaning code
    # ...
    
    # Split the data
    train_df = df.sample(frac=0.8, random_state=42)
    test_df = df.drop(train_df.index)
    
    x_train = train_df.drop('target', axis=1)
    y_train = train_df['target']
    x_test = test_df.drop('target', axis=1)
    y_test = test_df['target']
    
    return x_train, x_test, y_train, y_test
```

The `Annotated` type enhances readability in the dashboard and makes it easier to retrieve specific artifacts later.

### Accessing Artifacts

You can access artifacts from past runs using the ZenML Client:

```python
from zenml.client import Client

# Get a specific run
client = Client()
pipeline_run = client.get_pipeline_run("<PIPELINE_RUN_ID>")

# Get an artifact from a specific step
step = pipeline_run.steps["clean_data"]
x_train = step.outputs["x_train"].load()

# Use the artifact
print(x_train.shape)
```

### Artifact Naming Convention

ZenML uses a consistent naming pattern for artifacts:

```
<pipeline_name>.<step_name>.<output_name>
```

For example:
- `training_pipeline.create_data.output`
- `preprocessing_pipeline.split_data.X_train`

### Visualizing Artifacts

ZenML automatically provides visualizations for various data types, which can be viewed in the ZenML dashboard. You can also view visualizations in notebooks:

```python
from zenml.client import Client

# Get an artifact
client = Client()
artifact = client.get_artifact("<ARTIFACT_ID>")

# Display visualization
artifact.visualize()
```

For more details on artifact visualization, see [Visualizations](./visualizations.md).

### Deleting Artifacts

Individual artifacts cannot be deleted directly (to prevent broken references). However, you can clean up unused artifacts with:

```bash
zenml artifact prune
```

This command deletes artifacts that are no longer referenced by any pipeline runs.

## Advanced Topics

For more advanced topics related to artifacts, see:

- [Materializers](./materializers.md): Learn how to handle custom data types with materializers
- [Visualizations](./visualizations.md): Customize artifact visualizations

## Conclusion

Artifacts are a fundamental part of ZenML's pipeline architecture, providing versioning, lineage tracking, and reproducibility. By understanding how artifacts work, you can build more effective and maintainable ML pipelines. 