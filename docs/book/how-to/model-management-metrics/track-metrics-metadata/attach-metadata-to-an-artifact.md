---
description: Learn how to log metadata for artifacts and models in ZenML.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Attach metadata to an artifact

![Metadata in the dashboard](../../../.gitbook/assets/metadata-in-dashboard.png)

Metadata plays a critical role in ZenML, providing context and additional information about various entities within the platform. Anything which is `metadata` in ZenML can be compared in the dashboard.

This guide will explain how to log metadata for artifacts and models in ZenML and detail the types of metadata that can be logged.

## Logging Metadata for Artifacts

Artifacts in ZenML are outputs of steps within a pipeline, such as datasets, models, or evaluation results. Associating metadata with artifacts can help users understand the nature and characteristics of these outputs.

To log metadata for an artifact, you can use the `log_artifact_metadata` method. This method allows you to attach a dictionary of key-value pairs as metadata to an artifact. The metadata can be any JSON-serializable value, including custom classes such as `Uri`, `Path`, `DType`, and `StorageSize`. Find out more about these different types [here](../../model-management-metrics/track-metrics-metadata/logging-metadata.md).&#x20;

Here's an example of logging metadata for an artifact:

```python
from zenml import step, log_artifact_metadata
from zenml.metadata.metadata_types import StorageSize

@step
def process_data_step(dataframe: pd.DataFrame) ->  Annotated[pd.DataFrame, "processed_data"],:
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

## Fetching logged metadata

Once metadata has been logged in an artifact, or [step](../../model-management-metrics/track-metrics-metadata/attach-metadata-to-a-model.md), we can easily fetch the metadata with the ZenML Client:

```python
from zenml.client import Client

client = Client()
artifact = client.get_artifact_version("my_artifact", "my_version")

print(artifact.run_metadata["metadata_key"].value)
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

In the ZenML dashboard, "model\_metrics" and "data\_details" would appear as separate cards, each containing their respective key-value pairs.
<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>


