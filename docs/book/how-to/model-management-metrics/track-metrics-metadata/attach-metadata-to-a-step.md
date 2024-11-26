---
description: Learn how to attach metadata to a step.
---

# Attach metadata to a step

In ZenML, you can log metadata for a specific step during or after its 
execution by using the `log_metadata` function. This function allows you to 
attach a dictionary of key-value pairs as metadata to a step. The metadata 
can be any JSON-serializable value, including custom classes such as 
`Uri`, `Path`, `DType`, and `StorageSize`.

## Logging Metadata Within a Step

If called within a step, `log_metadata` automatically attaches the metadata to 
the currently executing step and its associated pipeline run. This is 
ideal for logging metrics or information that becomes available during the 
step execution.

```python
from typing import Annotated

import pandas as pd
from sklearn.base import ClassifierMixin
from sklearn.ensemble import RandomForestClassifier

from zenml import step, log_metadata, ArtifactConfig


@step
def train_model(dataset: pd.DataFrame) -> Annotated[
    ClassifierMixin,
    ArtifactConfig(name="sklearn_classifier")
]:
    """Train a model and log evaluation metrics."""
    classifier = RandomForestClassifier().fit(dataset)
    accuracy, precision, recall = ...

    # Log metadata at the step level
    log_metadata(
        metadata={
            "evaluation_metrics": {
                "accuracy": accuracy,
                "precision": precision,
                "recall": recall
            }
        }
    )
    return classifier
```

## Manually Logging Metadata a Step Run

You can also log metadata for a specific step after execution, using 
identifiers to specify the pipeline, step, and run. This approach is 
useful when you want to log metadata post-execution.

```python
from zenml import log_metadata

log_metadata(
    metadata={
        "additional_info": {"a_number": 3}
    },
    step_name="step_name",
    run_id_name_or_prefix="run_id_name_or_prefix"
)

# or 

log_metadata(
    metadata={
        "additional_info": {"a_number": 3}
    },
    step_id="step_id",
)
```

## Fetching logged metadata

Once metadata has been logged in a step, we can easily fetch the metadata with 
the ZenML Client:

```python
from zenml.client import Client

client = Client()
step = client.get_pipeline_run("pipeline_id").steps["step_name"]

print(step.run_metadata["metadata_key"])
```

{% hint style="info" %}
When you are fetching metadata using a specific key, the returned value will 
always reflect the latest entry.
{% endhint %}

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
