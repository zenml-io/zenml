---
description: Pause a dynamic pipeline for external input and resume it after the input is resolved.
icon: hourglass-half
---

# Wait for external input and resume a run

Use `zenml.wait(...)` when a dynamic pipeline needs a human or external system to provide input before it can continue.

{% hint style="info" %}
`zenml.wait(...)` only works inside [dynamic pipelines](./dynamic_pipelines.md). It does not work in static pipelines or inside a step.
{% endhint %}

## Basic pattern

When the pipeline reaches `wait(...)`, ZenML creates a wait condition and pauses the run. Once the condition is resolved, the pipeline continues from that point.

```python
from zenml import pipeline, step, wait


@step
def prepare_candidate() -> str:
    """Prepare the candidate that may be released."""
    return "model:v17"


@step
def register_release(candidate: str, release_tag: str) -> None:
    """Register the release tag chosen for the candidate."""
    print(f"Registering {candidate} as {release_tag}")


@pipeline(dynamic=True)
def release_pipeline() -> None:
    """Pause until an external system provides a release tag."""
    candidate = prepare_candidate()
    release_tag = wait(
        schema=str,
        question="Provide the release tag for this candidate.",
    )
    register_release(candidate=candidate, release_tag=release_tag)
```

## Data schemas

The `schema=` argument defines the shape of the value that must be returned when the wait condition is answered.
You can use primitive types such as:

- `str`
- `int`
- `float`
- `bool`
- `list`
- `dict`

You can also use Pydantic objects for structured input:

```python
from pydantic import BaseModel
from zenml import pipeline, wait


class DeploymentConfig(BaseModel):
    """Structured deployment input returned to the waiting run."""

    environment: str
    replicas: int
    notify_slack: bool


@pipeline(dynamic=True)
def deployment_pipeline() -> None:
    """Pause until a structured deployment configuration is provided."""
    config = wait(
        schema=DeploymentConfig,
        question="Provide the deployment configuration for this run.",
    )
    print(config.environment, config.replicas, config.notify_slack)
```

## Resolve and resume

You can resolve wait conditions either in the UI or from the CLI.

To review and resolve the pending wait conditions for a specific run interactively, use:
```bash
zenml pipeline runs wait-conditions resolve --run <RUN_ID_OR_NAME> --interactive
```

If you want to resolve a condition non-interactively, pass the result as JSON:

```bash
zenml pipeline runs wait-conditions resolve <WAIT_CONDITION_ID> \
  --resolution continue \
  --result '{"environment": "production", "replicas": 3, "notify_slack": true}'
```

In ZenML Pro, the run should start resuming automatically after the wait condition is resolved. If it remains paused, or if you are using OSS, resume it manually:

```bash
zenml pipeline runs resume <RUN_ID_OR_NAME>
```
