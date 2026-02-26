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

Call `.replay()` on any `@pipeline`-decorated function. ZenML resolves the run to replay using the first match:

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

### Skipping steps

You can skip steps that don't need to be re-executed. Skipped steps reuse
their output artifacts from the original run.

```python
# Skip specific steps by name
training_pipeline.replay(skip=["load_data"])

# Automatically skip all steps that succeeded in the original run
training_pipeline.replay(skip_successful_steps=True)
```

{% hint style="info" %}
A step can only be skipped if all of its upstream dependencies are also skipped.
{% endhint %}

### Overriding pipeline parameters

Pass `input_overrides` to change parameters for the replayed run. Any
parameters you don't override are carried over from the original run.

```python
training_pipeline.replay(input_overrides={"learning_rate": 0.01})
```

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

