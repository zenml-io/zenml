---
description: >-
  Learn how ZenML manages data artifacts, tracks versioning and lineage, and
  enables effective data flow between steps.
icon: binary
---

# Artifacts

Artifacts are a cornerstone of ZenML's ML pipeline management system. This guide explains what artifacts are, how they work, and how to use them effectively in your pipelines.

### Artifacts in the Pipeline Workflow

Here's how artifacts fit into the ZenML pipeline workflow:

1. A step produces data as output
2. ZenML automatically stores this output as an artifact
3. Other steps can use this artifact as input
4. ZenML tracks the relationships between artifacts and steps

This system creates a complete data lineage for every artifact in your ML workflows, enabling reproducibility and traceability.

## Basic Artifact Usage

### Creating Artifacts (Step Outputs)

Any value returned from a step becomes an artifact:

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
def create_prompt_template() -> str:
    """Creates a prompt template that becomes an artifact."""
    return """
    You are a helpful customer service agent. 
    
    Customer Query: {query}
    Previous Context: {context}
    
    Please provide a helpful response following our company guidelines.
    """
```

### Consuming Artifacts (Step Inputs)

You can use artifacts by receiving them as inputs to other steps:

```python
@step
def process_data(df: pd.DataFrame) -> pd.DataFrame:
    """Takes an artifact as input and returns a new artifact."""
    df["feature_3"] = df["feature_1"] * df["feature_2"]
    return df

@step
def test_agent_response(prompt_template: str, test_query: str) -> dict:
    """Uses a prompt template artifact to test agent responses."""
    filled_prompt = prompt_template.format(
        query=test_query, 
        context="Previous customer complained about delayed shipping"
    )
    # Your agent logic here
    response = call_llm_agent(filled_prompt)
    return {"query": test_query, "response": response, "prompt_used": filled_prompt}

@pipeline
def simple_pipeline():
    """Pipeline that creates and processes artifacts."""
    # Traditional ML artifacts
    data = create_data()  # Produces an artifact
    processed_data = process_data(data)  # Uses and produces artifacts
    
    # AI agent artifacts
    prompt = create_prompt_template()  # Produces a prompt artifact
    agent_test = test_agent_response(prompt, "Where is my order?")  # Uses prompt artifact
```

### Artifacts vs. Parameters

When calling a step, inputs can be either artifacts or parameters:

* **Artifacts** are outputs from other steps in the pipeline. They are tracked, versioned, and stored in the artifact store.
* **Parameters** are literal values provided directly to the step. They aren't stored as artifacts but are recorded with the pipeline run.

```python
import pandas as pd
from zenml import step, pipeline

@step
def train_model(data: pd.DataFrame, learning_rate: float) -> object:
    """Step with both artifact and parameter inputs."""
    # data is an artifact (output from another step)
    # learning_rate is a parameter (literal value)
    # Note: create_model would be your own model creation function
    model = create_model(learning_rate)
    model.fit(data)
    return model

@pipeline
def training_pipeline():
    # data is an artifact
    data = create_data()
    
    # data is passed as an artifact, learning_rate as a parameter
    model = train_model(data=data, learning_rate=0.01)
```

Parameters are limited to JSON-serializable values (numbers, strings, lists, dictionaries, etc.). More complex objects should be passed as artifacts.

### Accessing Artifacts After Pipeline Runs

You can access artifacts from completed runs using the ZenML Client:

```python
from zenml.client import Client

# Get a specific run
client = Client()
pipeline_run = client.get_pipeline_run("<PIPELINE_RUN_ID>")

# Get an artifact from a specific step
train_data = pipeline_run.steps["split_data"].outputs["train_data"].load()

# Use the artifact
print(train_data.shape)
```

## Working with Artifact Types

### Type Annotations

Type annotations are important when working with artifacts as they:
1. Help ZenML select the appropriate materializer for storage
2. Validate inputs and outputs at runtime
3. Document the data flow of your pipeline

```python
from typing import Tuple
import numpy as np
import pandas as pd
from zenml import step

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

ZenML supports many common data types out of the box:
* Primitive types (`int`, `float`, `str`, `bool`)
* Container types (`dict`, `list`, `tuple`)
* NumPy arrays
* Pandas DataFrames
* Many ML model formats (through integrations)

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

### Naming Your Artifacts

By default, artifacts are named based on their position or variable name:
* Single outputs are named `output`
* Multiple outputs are named `output_0`, `output_1`, etc.

You can give your artifacts more meaningful names using the `Annotated` type:

```python
from typing import Tuple
from typing import Annotated
import pandas as pd
from zenml import step

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
from typing import Annotated
import pandas as pd
from zenml import step, pipeline

@step
def extract_data(source: str) -> Annotated[pd.DataFrame, "{dataset_type}_data"]:
    """Extract data with a dynamically named output."""
    # Implementation...
    data = pd.DataFrame()  # Your data extraction logic here
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
* `{date}`: Current date (e.g., "2023_06_15")
* `{time}`: Current time (e.g., "14_30_45_123456")
* Custom placeholders can be defined using `substitutions`

## How Artifacts Work Under the Hood

### Materializers: How Data Gets Stored

Materializers are a key concept in ZenML's artifact system. They handle:

* **Serializing data** when saving artifacts to storage
* **Deserializing data** when loading artifacts from storage
* **Generating visualizations** for the dashboard
* **Extracting metadata** for tracking and searching

When a step produces an output, ZenML automatically selects the appropriate materializer based on the data type (using type annotations). ZenML includes built-in materializers for common data types like:

* Primitive types (`int`, `float`, `str`, `bool`)
* Container types (`dict`, `list`, `tuple`)
* NumPy arrays, Pandas DataFrames and many other ML-related formats (through integrations)

Here's how materializers work in practice:

```python
from zenml import step
from sklearn.linear_model import LinearRegression

@step
def train_model(X_train, y_train) -> LinearRegression:
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

## Advanced Artifact Usage

### Accessing Artifacts from Previous Runs

You can access artifacts from any previous run by name or ID:

```python
from zenml.client import Client

# Get a specific artifact version
artifact = Client().get_artifact_version("my_model", "1.0")

# Get the latest version of an artifact
latest_artifact = Client().get_artifact_version("my_model")

# Load it into memory
model = latest_artifact.load()
```

You can also access artifacts within steps:

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

### Cross-Pipeline Artifact Usage

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

### Visualizing Artifacts

ZenML automatically generates visualizations for many types of artifacts, viewable in the dashboard:

```python
# You can also view visualizations in notebooks
from zenml.client import Client

artifact = Client().get_artifact_version("<ARTIFACT_NAME>")
artifact.visualize()
```

For detailed information on visualizations, see [Visualizations](visualizations.md).

### Managing Artifacts

Individual artifacts cannot be deleted directly (to prevent broken references). However, you can clean up unused artifacts:

```bash
zenml artifact prune
```

This deletes artifacts that are no longer referenced by any pipeline run. You can control this behavior with flags:

* `--only-artifact`: Only delete the physical files, keep database entries
* `--only-metadata`: Only delete database entries, keep files
* `--ignore-errors`: Continue pruning even if some artifacts can't be deleted
* `--threads` / `-t`: Enable parallel deletion for faster pruning when dealing with many artifacts

### Registering Existing Data as Artifacts

Sometimes, you may have data created externally (outside of ZenML pipelines) that you want to use within your ZenML workflows. Instead of reading and materializing this data within a step, you can register existing files or folders as ZenML artifacts directly.

#### Register an Existing Folder

To register a folder as a ZenML artifact:

```python
from zenml.client import Client
from zenml import register_artifact
import os
from pathlib import Path

# Path to an existing folder in your artifact store
prefix = Client().active_stack.artifact_store.path
existing_folder = os.path.join(prefix, "my_folder")

# Register it as a ZenML artifact
register_artifact(
    folder_or_file_uri=existing_folder,
    name="my_folder_artifact"
)

# Later, load the artifact
folder_path = Client().get_artifact_version("my_folder_artifact").load()
assert isinstance(folder_path, Path)
assert os.path.isdir(folder_path)
```

#### Register an Existing File

Similarly, you can register individual files:

```python
from zenml.client import Client
from zenml import register_artifact
import os
from pathlib import Path

# Path to an existing file in your artifact store
prefix = Client().active_stack.artifact_store.path
existing_file = os.path.join(prefix, "my_folder/model.pkl")

# Register it as a ZenML artifact
register_artifact(
    folder_or_file_uri=existing_file,
    name="my_model_artifact"
)

# Later, load the artifact
file_path = Client().get_artifact_version("my_model_artifact").load()
assert isinstance(file_path, Path)
assert not os.path.isdir(file_path)
```

This approach is particularly useful for:
* Integrating with external ML frameworks that save their own data
* Working with pre-existing datasets
* Registering model checkpoints created during training

When you load these artifacts, you'll receive a `pathlib.Path` pointing to a temporary location in your executing environment, ready for use as a normal local path.

#### Register Framework Checkpoints

A common use case is registering model checkpoints from training frameworks like PyTorch Lightning:

```python
import os
from uuid import uuid4
from zenml.client import Client
from zenml import register_artifact
from pytorch_lightning import Trainer
from pytorch_lightning.callbacks import ModelCheckpoint

# Define checkpoint location in your artifact store
prefix = Client().active_stack.artifact_store.path
checkpoint_dir = os.path.join(prefix, uuid4().hex)

# Configure PyTorch Lightning trainer with checkpointing
model = YourLightningModel()
trainer = Trainer(
    default_root_dir=checkpoint_dir,
    callbacks=[
        ModelCheckpoint(
            every_n_epochs=1, 
            save_top_k=-1,  # Keep all checkpoints
            filename="checkpoint-{epoch:02d}"
        )
    ],
)

# Train the model
trainer.fit(model)

# Register all checkpoints as a ZenML artifact
register_artifact(
    folder_or_file_uri=checkpoint_dir, 
    name="lightning_checkpoints"
)

# Later, you can load the checkpoint folder
checkpoint_path = Client().get_artifact_version("lightning_checkpoints").load()
```

You can also extend the `ModelCheckpoint` callback to register each checkpoint as a separate artifact version during training. This approach enables better version control of intermediate checkpoints.

## Conclusion

Artifacts are a central part of ZenML's approach to ML pipelines. They provide:

* Automatic versioning and lineage tracking
* Efficient storage and caching
* Type-safe data handling
* Visualization capabilities
* Cross-pipeline data sharing

Whether you're working with traditional ML models, prompt templates, agent configurations, or evaluation datasets, ZenML's artifact system treats them all uniformly. This enables you to apply the same MLOps principles across your entire AI stack - from classical ML to complex multi-agent systems.

By understanding how artifacts work, you can build more effective, maintainable, and reproducible ML pipelines and AI workflows.

For more information on specific aspects of artifacts, see:

* [Materializers](materializers.md): Creating custom serializers for your data types
* [Visualizations](visualizations.md): Customizing artifact visualizations