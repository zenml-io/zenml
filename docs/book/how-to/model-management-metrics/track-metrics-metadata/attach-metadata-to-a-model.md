---
description: Learn how to attach metadata to a model.
---

# Attach metadata to a model

ZenML allows you to log metadata for models, which provides additional context
that goes beyond individual artifact details. Model metadata can represent
high-level insights, such as evaluation results, deployment information,
or customer-specific details, making it easier to manage and interpret
the model's usage and performance across different versions.

## Logging Metadata for Models

To log metadata for a model, use the `log_metadata` function. This function
lets you attach key-value metadata to a model, which can include metrics and
other JSON-serializable values, such as custom ZenML types like `Uri`,
`Path`, and `StorageSize`.

Here's an example of logging metadata for a model:

```python
from typing import Annotated

import pandas as pd
from sklearn.base import ClassifierMixin
from sklearn.ensemble import RandomForestClassifier

from zenml import step, log_metadata, ArtifactConfig, get_step_context


@step
def train_model(dataset: pd.DataFrame) -> Annotated[
    ClassifierMixin, ArtifactConfig(name="sklearn_classifier")
]:
    """Train a model and log model metadata."""
    classifier = RandomForestClassifier().fit(dataset)
    accuracy, precision, recall = ...
    
    log_metadata(
        metadata={
            "evaluation_metrics": {
                "accuracy": accuracy,
                "precision": precision,
                "recall": recall
            }
        },
        infer_model=True,
    )

    return classifier
```

In this example, the metadata is associated with the model rather than the
specific classifier artifact. This is particularly useful when the metadata
reflects an aggregation or summary of various steps and artifacts in the
pipeline.


### Selecting Models with `log_metadata`

When using `log_metadata`, ZenML provides flexible options of attaching 
metadata to model versions:

1. **Using `infer_model`**: If used within a step, ZenML will use the step
   context to infer the model it is using and attach the metadata to it.
2. **Model Name and Version Provided**: If both a model name and version are
   provided, ZenML will use these to identify and attach metadata to the
   specific model version.
3. **Model Version ID Provided**: If a model version ID is directly provided,
   ZenML will use it to fetch and attach the metadata to that specific model
   version.

## Fetching logged metadata

Once metadata has been attached to a model, it can be retrieved for inspection
or analysis using the ZenML Client.

```python
from zenml.client import Client

client = Client()
model = client.get_model_version("my_model", "my_version")

print(model.run_metadata["metadata_key"])
```

{% hint style="info" %}
When you are fetching metadata using a specific key, the returned value will 
always reflect the latest entry.
{% endhint %}

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
