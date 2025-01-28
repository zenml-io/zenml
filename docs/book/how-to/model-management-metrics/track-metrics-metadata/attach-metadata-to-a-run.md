---
description: Learn how to attach metadata to a run.
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
pipeline run where the metadata key will have the `step_name::metadata_key` 
pattern. This allows you to use the same metadata key from different steps 
while the run's still executing.

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

## Manually Logging Metadata to a Pipeline Run

You can also attach metadata to a specific pipeline run without needing a step, 
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

{% hint style="info" %}
When you are fetching metadata using a specific key, the returned value will 
always reflect the latest entry.
{% endhint %}

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
