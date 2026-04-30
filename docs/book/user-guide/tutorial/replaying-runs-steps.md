---
description: Re-run pipelines or individual steps using artifacts from a previous execution.
icon: rotate-right
---

# Replaying past runs

A replay re-executes a pipeline or step using the same input artifacts (and parameters) as a previous run. This is useful when you want to:

- **Debug a failed step** without re-running the entire pipeline.
- **Re-run a pipeline after a code fix**, skipping steps that already succeeded.
- **Test local changes** against production data by replaying in debug mode.

---

## Replaying a pipeline

Replay a pipeline either from local pipeline code (`.replay()`) or directly via
the server (`Client().replay_pipeline_run(...)`).

{% tabs %}
{% tab title="From local code" %}

ZenML resolves the run to replay using the first match:

1. `pipeline_run` — replay that exact run.
2. `pipeline` — replay the latest run of that pipeline name/ID.
3. Neither — replay the latest run whose name matches the current pipeline instance.

```python
from zenml import pipeline, step

@step
def load_data() -> dict:
    ...

@step
def train(data: dict) -> None:
    ...

@pipeline
def training_pipeline(data: dict):
    train(data=load_data())

# Replay the latest run of this pipeline
training_pipeline.replay()

# Replay a specific run
training_pipeline.replay(pipeline_run="run_name_or_id")
```
{% endtab %}

{% tab title="From the server" %}
```python
from zenml import Client

# Replay a specific run by name or ID
Client().replay_pipeline_run(name_id_or_prefix="run_name_or_id")
```
{% endtab %}
{% endtabs %}

### Skipping steps

You can skip steps that don't need to be re-executed. Skipped steps reuse
their output artifacts from the original run.

{% tabs %}
{% tab title="From local code" %}
```python
# Skip specific steps by name
training_pipeline.replay(skip=["load_data"])

# Automatically skip all steps that succeeded in the original run
training_pipeline.replay(skip_successful_steps=True)
```
{% endtab %}

{% tab title="From the server" %}
```python
from zenml import Client

# Skip specific steps by invocation ID
Client().replay_pipeline_run(
    name_id_or_prefix="run_name_or_id",
    run_configuration={"steps_to_skip": ["load_data"]},
)

# Automatically skip all steps that succeeded in the original run
Client().replay_pipeline_run(
    name_id_or_prefix="run_name_or_id",
    run_configuration={"skip_successful_steps": True},
)
```
{% endtab %}
{% endtabs %}

{% hint style="info" %}
A step can only be skipped if all of its upstream dependencies are also skipped.
{% endhint %}

### Overriding pipeline parameters

{% tabs %}
{% tab title="From local code" %}
Pass `input_overrides` to change parameters for the replayed run. Any
parameters you don't override are carried over from the original run.

```python
training_pipeline.replay(input_overrides={"learning_rate": 0.01})
```
{% endtab %}
{% tab title="From the server" %}
Pass `parameters` in the run configuration to override pipeline parameters.

```python
from zenml import Client

Client().replay_pipeline_run(
    name_id_or_prefix="run_name_or_id",
    run_configuration={"parameters": {"learning_rate": 0.01}},
)
```
{% endtab %}
{% endtabs %}

### Overriding step inputs

Use `step_input_overrides` to replace specific step inputs for a replayed
pipeline run.

{% tabs %}
{% tab title="From local code" %}
`step_input_overrides` expects a mapping of `invocation_id -> input_name ->
value`.

```python
training_pipeline.replay(
    pipeline_run="run_name_or_id",
    step_input_overrides={
        "trainer": {
            "training_data": my_dataframe,
        }
    },
)
```
{% endtab %}
{% tab title="From the server" %}
For server-side replay, `step_input_overrides` values can be either:

- **UUIDs** of existing artifact versions (no new upload), or
- **inline values** (server uploads them to the active artifact store before
  replay starts).

```python
from zenml import Client
from uuid import UUID

Client().replay_pipeline_run(
    name_id_or_prefix="run_name_or_id",
    run_configuration={
        "step_input_overrides": {
            "trainer": {
                # Existing artifact version UUID: no upload
                "training_data": UUID("34e8ef74-32b9-4e58-ab8b-99ee133f4f89"),
                # Inline value: uploaded by the server
                "learning_rate": 0.01,
            }
        }
    },
)
```
{% endtab %}
{% endtabs %}

---

## Replaying a single step

Call `.replay()` on any `@step`-decorated function. ZenML loads the
original input artifacts, feeds them to your (potentially updated) step code,
and runs it as a single-step pipeline on the active stack.

The step to replay is resolved using the first match:

1. `step_run_id` — replay that exact step run.
2. `pipeline_run` + optional `invocation_id` — find the step in that run.
3. `pipeline` + optional `invocation_id` — find the step in the latest run of that pipeline.

```python
# Replay the step from the latest run of a pipeline
train.replay(pipeline="training_pipeline")

# Replay from a specific pipeline run
train.replay(pipeline_run="run_name_or_id")

# Replay a specific step run by ID
train.replay(step_run_id=step_run_uuid)
```

### Overriding inputs

You can replace any of the original input artifacts with new values:

```python
import pandas as pd

train.replay(
    pipeline="training_pipeline",
    input_overrides={"X_train": my_new_dataframe},
)
```

### Using `invocation_id`

If a step appears more than once in a pipeline, specify which invocation to
replay:

```python
train.replay(pipeline="training_pipeline", invocation_id="train_2")
```

---

## Debug mode

Both pipeline and step replays accept `debug=True`. This runs the replay
on a **local orchestrator** while keeping the rest of your active stack
(artifact store, etc.), so you can iterate quickly without waiting for remote
infrastructure.

```python
training_pipeline.replay(debug=True)
train.replay(pipeline="training_pipeline", debug=True)
```


<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
