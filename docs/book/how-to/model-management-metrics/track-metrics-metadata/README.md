---
icon: ufo-beam
description: Tracking metrics and metadata
---

# Track metrics and metadata

ZenML provides a unified way to log and manage metrics and metadata through 
the `log_metadata` function. This versatile function allows you to log 
metadata across various entities like models, artifacts, steps, and runs 
through a single interface. Additionally, you can adjust if you want to 
automatically the same metadata for the related entities.

### The most basic use-case

You can use the `log_metadata` function within a step:

```python
from zenml import step, log_metadata

@step
def my_step() -> ...:
    log_metadata(metadata={"accuracy": 0.91})
    ...
```

This will log the `accuracy` for the step, its pipeline run, and if provided 
its model version.

### Additional use-cases

The `log_metadata` function also supports various use-cases by allowing you to 
specify the target entity (e.g., model, artifact, step, or run) with flexible 
parameters. You can learn more about these use-cases in the following pages:

- [Log metadata to a step](attach-metadata-to-a-step.md)
- [Log metadata to a run](attach-metadata-to-a-run.md)
- [Log metadata to an artifact](attach-metadata-to-an-artifact.md)
- [Log metadata to a model](attach-metadata-to-a-model.md)

{% hint style="warning" %}
The older methods for logging metadata to specific entities, such as 
`log_model_metadata`, `log_artifact_metadata`, and `log_step_metadata`, are 
now deprecated. It is recommended to use `log_metadata` for all future 
implementations.
{% endhint %}

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
