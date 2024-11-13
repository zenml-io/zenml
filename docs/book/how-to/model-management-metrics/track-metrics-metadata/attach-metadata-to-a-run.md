---
description: Attaching metadata to a run.
---

# Attach Metadata to a Run

In ZenML, you can log metadata directly to a pipeline run, either during or 
after execution, using the `log_metadata` function. This function allows you 
to attach a dictionary of key-value pairs as metadata to a pipeline run, 
with values that can be any JSON-serializable data type, including ZenML 
custom types like `Uri`, `Path`, `DType`, and `StorageSize`.

## Logging Metadata Within a Run

If you are logging metadata from within a step that’s part of a pipeline run, 
calling `log_metadata` will attach the specified metadata to the current 
pipeline run. This is especially useful for logging details about the run 
while it's still active.

```python
from typing import Annotated

import pandas as pd
from sklearn.base import ClassifierMixin
from sklearn.ensemble import RandomForestClassifier

from zenml import step, log_metadata, ArtifactConfig


@step
def train_model(dataset: pd.DataFrame) -> Annotated[
    ClassifierMixin,
    ArtifactConfig(name="sklearn_classifier", is_model_artifact=True)
]:
    """Train a model and log run-level metadata."""
    classifier = RandomForestClassifier().fit(dataset)
    accuracy, precision, recall = ...

    # Log metadata at the run level
    log_metadata(
        metadata={
            "run_metrics": {
                "accuracy": accuracy,
                "precision": precision,
                "recall": recall
            }
        }
    )
    return classifier
```

{% hint style="warning" %}
In order to log metadata to a pipeline run during the step execution without 
specifying any additional identifiers, `log_related_entities` should be 
`True` (default behaviour).
{% endhint %}

## Logging Metadata Outside a Run

You can also attach metadata to a specific pipeline run after its execution, 
using identifiers like the run ID. This is useful when logging information or 
metrics that were calculated post-execution.

```python
from zenml import log_metadata

log_metadata(
    metadata={"post_run_info": {"some_metric": 5.0}},
    run_id_name_or_prefix="run_id_name_or_prefix"
)
```

## Fetching Logged Metadata

Once metadata has been logged in a pipeline run, you can retrieve it using 
the ZenML Client:

```python
from zenml.client import Client

client = Client()
run = client.get_pipeline_run("run_id_name_or_prefix")

print(run.run_metadata["metadata_key"])
```