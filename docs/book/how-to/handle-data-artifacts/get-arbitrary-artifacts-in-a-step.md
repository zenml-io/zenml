---
description: >-
  Not all artifacts need to come through the step interface from direct upstream
  steps.
---

# Get arbitrary artifacts in a step

As described in [the metadata guide](../metadata/logging-metadata.md), the metadata can be fetched with the client, and this is how you would use it to fetch it within a step. This allows you to fetch artifacts from other upstream steps or even completely different pipelines.

```python
from zenml.client import Client
from zenml import step

@step
def my_step():
    client = Client()
    # Directly fetch an artifact
    output = client.get_artifact_version("my_dataset", "my_version")
    output.run_metadata["accuracy"].value
```
