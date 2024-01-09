---
description: Tracking your metadata.
---

# Logging metadata

Metadata plays a critical role in ZenML, providing context and additional information about various entities within the platform. Anything which is `metadata` in ZenML can be compared in the dashboard.

This guide will explain how to log metadata for artifacts and model versions in ZenML and detail the types of metadata that can be logged.

## Logging Metadata for Artifacts

Artifacts in ZenML are outputs of steps within a pipeline, such as datasets, models, or evaluation results. Associating metadata with artifacts can help users understand the nature and characteristics of these outputs.

To log metadata for an artifact, you can use the `log_artifact_metadata` method. This method allows you to attach a dictionary of key-value pairs as metadata to an artifact. The metadata can be any JSON-serializable value, including custom classes such as `Uri`, `Path`, `DType`, and `StorageSize`.

Here's an example of logging metadata for an artifact:

```python
from zenml import step, log_artifact_metadata

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

## Logging Metadata for Model Versions

While artifact metadata is specific to individual outputs of steps, model version metadata encapsulates broader and more general information that spans across multiple artifacts. For example, evaluation results or the name of a customer for whom the model is intended could be logged with the model version.

Here's an example of logging metadata for a model version:

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

    # Log metadata for the model version
    # This associates the metadata with the ZenML model version, not the artifact
    log_model_metadata(
        metadata={
            "evaluation_metrics": {
                "accuracy": accuracy,
                "precision": precision,
                "recall": recall
            }
        },
        # Omitted model_name will use the model version in the current context
        model_name="zenml_model_name",
        # Omitted model_version will default to 'latest'
        model_version="zenml_model_version",
    )
    return classifier
```

In this example, the metadata is associated with the model version rather than the specific classifier artifact. This is particularly useful when the metadata reflects an aggregation or summary of various steps and artifacts in the pipeline.

## Grouping Metadata in the Dashboard

When logging metadata passing a dictionary of dictionaries in the `metadata` parameter will group the metadata into cards in the ZenML dashboard. This feature helps organize metadata into logical sections, making it easier to visualize and understand.

Here's an example of grouping metadata into cards:

```python
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

Choosing whether to log metadata with artifacts or model versions depends on the scope and purpose of the information you wish to capture. Artifact metadata is best for details specific to individual outputs, while model version metadata is suitable for broader information relevant to the overall model. By utilizing ZenML's metadata logging capabilities and special types, you can enhance the traceability, reproducibility, and analysis of your ML workflows.

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>