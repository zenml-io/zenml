---
description: Tracking your metadata.
---

# Logging metadata

Metadata plays a critical role in ZenML, providing context and additional information about various entities within the platform. Anything which is `metadata` in ZenML can be compared in the dashboard.

This guide will explain how to log metadata for artifacts and models in ZenML and detail the types of metadata that can be logged.

## Logging

### Logging Metadata for Artifacts

Artifacts in ZenML are outputs of steps within a pipeline, such as datasets, models, or evaluation results. Associating metadata with artifacts can help users understand the nature and characteristics of these outputs.

To log metadata for an artifact, you can use the `log_artifact_metadata` method. This method allows you to attach a dictionary of key-value pairs as metadata to an artifact. The metadata can be any JSON-serializable value, including custom classes such as `Uri`, `Path`, `DType`, and `StorageSize`.

Here's an example of logging metadata for an artifact:

```python
from zenml import step, log_artifact_metadata
from zenml.metadata.metadata_types import StorageSize

@step
def process_data_step(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Process a dataframe and log metadata about the result."""
    # Perform processing on the dataframe...
    processed_dataframe = ...

    # Log metadata about the processed dataframe
    log_artifact_metadata(
        artifact_name="processed_data",
        metadata={
            "row_count": len(processed_dataframe),
            "columns": list(processed_dataframe.columns),
            "storage_size": StorageSize(processed_dataframe.memory_usage().sum())
        }
    )
    return processed_dataframe
```

### Logging Metadata for Models

While artifact metadata is specific to individual outputs of steps, model metadata encapsulates broader and more general information that spans across multiple artifacts. For example, evaluation results or the name of a customer for whom the model is intended could be logged with the model.

Here's an example of logging metadata for a model:

```python
from zenml import step, log_model_metadata, ArtifactConfig, get_step_context
from typing import Annotated
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.base import ClassifierMixin

@step
def train_model(dataset: pd.DataFrame) -> Annotated[ClassifierMixin, ArtifactConfig(name="sklearn_classifier", is_model_artifact=True)]:
    """Train a model"""
    # Fit the model and compute metrics
    classifier = RandomForestClassifier().fit(dataset)
    accuracy, precision, recall = ...

    # Log metadata for the model
    # This associates the metadata with the ZenML model, not the artifact
    log_model_metadata(
        metadata={
            "evaluation_metrics": {
                "accuracy": accuracy,
                "precision": precision,
                "recall": recall
            }
        },
        # Omitted model_name will use the model in the current context
        model_name="zenml_model_name",
        # Omitted model_version will default to 'latest'
        model_version="zenml_model_version",
    )
    return classifier
```

In this example, the metadata is associated with the model rather than the
specific classifier artifact. This is particularly useful when the metadata
reflects an aggregation or summary of various steps and artifacts in the
pipeline.

### Logging Metadata for Steps

You might want to log metadata and have that be attached to a specific step
during the course of your work. This is possible by using the
`log_step_metadata`
method. This method allows you to attach a dictionary of key-value pairs as
metadata to a step. The metadata can be any JSON-serializable value, including
custom classes such as `Uri`, `Path`, `DType`, and `StorageSize`.

You can call this method from within a step or from outside. If you call it from
within it will attach the metadata to the step and run that is currently being
executed.

```python
from zenml import step, log_step_metadata, ArtifactConfig, get_step_context
from typing import Annotated
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.base import ClassifierMixin

@step
def train_model(dataset: pd.DataFrame) -> Annotated[ClassifierMixin, ArtifactConfig(name="sklearn_classifier", is_model_artifact=True)]:
    """Train a model"""
    # Fit the model and compute metrics
    classifier = RandomForestClassifier().fit(dataset)
    accuracy, precision, recall = ...

    # Log metadata at the step level
    # This associates the metadata with the ZenML step run
    log_step_metadata(
        metadata={
            "evaluation_metrics": {
                "accuracy": accuracy,
                "precision": precision,
                "recall": recall
            }
        },
    )
    return classifier
```


If you call it from outside you can attach the metadata to a specific step run
from any pipeline and step. This is useful if you want to attach the metadata
after you've run the step.

```python
from zenml import log_step_metadata
# run some step

# subsequently log the metadata for the step
log_step_metadata(
        metadata={
            "some_metadata": {
                "a_number": 3,
            }
        },
        pipeline_name_id_or_prefix="my_pipeline",
        step_name="my_step",
        run_id="my_step_run_id"
    )
```

## Fetching logged metadata

Once metadata has been logged in an [artifact](#logging-metadata-for-artifacts), [model](#logging-metadata-for-models), or [step](#logging-metadata-for-steps), we can easily fetch the metadata with the ZenML Client:

```python
from zenml.client import Client

client = Client()

artifact = client.get_artifact_version("my_artifact", "my_version")

model = client.get_model_version("my_model", "my_version")

step = client.get_pipeline_run().steps["step_name"]

print(artifact.run_metadata["metadata_key"].value)
print(model.run_metadata["metadata_key"].value)
print(step.run_metadata["metadata_key"].value)
```

## Grouping Metadata in the Dashboard

When logging metadata passing a dictionary of dictionaries in the `metadata` parameter will group the metadata into cards in the ZenML dashboard. This feature helps organize metadata into logical sections, making it easier to visualize and understand.

Here's an example of grouping metadata into cards:

```python
from zenml.metadata.metadata_types import StorageSize

log_artifact_metadata(
    metadata={
        "model_metrics": {
            "accuracy": 0.95,
            "precision": 0.92,
            "recall": 0.90
        },
        "data_details": {
            "dataset_size": StorageSize(1500000),
            "feature_columns": ["age", "income", "score"]
        }
    }
)
```

In the ZenML dashboard, "model_metrics" and "data_details" would appear as separate cards, each containing their respective key-value pairs.

## Examples of Special Metadata Types

ZenML supports several special metadata types to capture specific kinds of information. Here are examples of how to use the special types `Uri`, `Path`, `DType`, and `StorageSize`:

```python
from zenml.metadata.metadata_types import StorageSize, DType

log_artifact_metadata(
    metadata={
        "dataset_source": Uri("gs://my-bucket/datasets/source.csv"),
        "preprocessing_script": Path("/scripts/preprocess.py"),
        "column_types": {
            "age": DType("int"),
            "income": DType("float"),
            "score": DType("int")
        },
        "processed_data_size": StorageSize(2500000)
    }
)
```

In this example:

- `Uri` is used to indicate a dataset source URI.
- `Path` is used to specify the filesystem path to a preprocessing script.
- `DType` is used to describe the data types of specific columns.
- `StorageSize` is used to indicate the size of the processed data in bytes.

These special types help standardize the format of metadata and ensure that it is logged in a consistent and interpretable manner.

## Conclusion

Choosing whether to log metadata with artifacts or models depends on the scope and purpose of the information you wish to capture. Artifact metadata is best for details specific to individual outputs, while model metadata is suitable for broader information relevant to the overall model. By utilizing ZenML's metadata logging capabilities and special types, you can enhance the traceability, reproducibility, and analysis of your ML workflows.

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
