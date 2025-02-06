---
description: >-
  Not all artifacts need to come through the step interface from direct upstream
  steps.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Get arbitrary artifacts in a step

As described in [the metadata guide](../../model-management-metrics/track-metrics-metadata/logging-metadata.md), the metadata can be fetched with the client, and this is how you would use it to fetch it within a step. This allows you to fetch artifacts from other upstream steps or even completely different pipelines.

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

This is one of the ways you can access artifacts that have already been created
and stored in the artifact store. This can be useful when you want to use
artifacts from other pipelines or steps that are not directly upstream.

## See Also

- [Managing artifacts](../../../user-guide/starter-guide/manage-artifacts.md) -
  learn about the `ExternalArtifact` type and how to pass artifacts between steps.

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
