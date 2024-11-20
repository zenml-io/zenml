---
description: >-
  Attach any metadata as key-value pairs to your models for future reference and
  auditability.
---

# Attach metadata to a model

## Logging Metadata for Models

While artifact metadata is specific to individual outputs of steps, model metadata encapsulates broader and more general information that spans across multiple artifacts. For example, evaluation results or the name of a customer for whom the model is intended could be logged with the model.

Here's an example of logging metadata for a model:

```python
from zenml import step, log_model_metadata, ArtifactConfig, get_step_context
from typing import Annotated
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.base import ClassifierMixin

@step
def train_model(dataset: pd.DataFrame) -> Annotated[ClassifierMixin, ArtifactConfig(name="sklearn_classifier")]:
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

In this example, the metadata is associated with the model rather than the specific classifier artifact. This is particularly useful when the metadata reflects an aggregation or summary of various steps and artifacts in the pipeline.

## Fetching logged metadata

Once metadata has been logged in an [artifact](attach-metadata-to-an-artifact.md), model, or [step](attach-metadata-to-steps.md), we can easily fetch the metadata with the ZenML Client:

```python
from zenml.client import Client

client = Client()
model = client.get_model_version("my_model", "my_version")

print(model.run_metadata["metadata_key"].value)
```

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
