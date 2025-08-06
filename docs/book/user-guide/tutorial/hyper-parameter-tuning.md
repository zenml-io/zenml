---
description: Running a hyperparameter tuning trial with ZenML.
icon: itunes-note
---

# Hyper-parameter tuning

## Introduction

Hyper‑parameter tuning is the process of systematically searching for the best set of hyper‑parameters for your model.  In ZenML, you can express these experiments declaratively inside a pipeline so that every trial is tracked, reproducible and shareable.

In this tutorial you will:

1. Build a simple training `step` that takes a hyper‑parameter as input.
2. Create a **fan‑out / fan‑in** pipeline that trains multiple models in parallel – one for each hyper‑parameter value.
3. Select the best performing model.
4. Run the pipeline and inspect the results in the ZenML dashboard or programmatically.

{% hint style="info" %}
This tutorial focuses on the mechanics of orchestrating a grid‑search with ZenML.  For more advanced approaches (random search, Bayesian optimization, …) or a ready‑made example have a look at the [E2E example](https://github.com/zenml-io/zenml/tree/main/examples/e2e) mentioned at the end of the page.
{% endhint %}

### Prerequisites

* ZenML installed and an active stack (the local default stack is fine)
* `scikit‑learn` installed (`pip install scikit-learn`)
* Basic familiarity with ZenML pipelines and steps

---

## Step 1 Define the training step

Create a training step that accepts the learning‑rate as an input parameter and returns both the trained model and its training accuracy:

```python
from typing import Annotated
from sklearn.base import ClassifierMixin
from zenml import step

MODEL_OUTPUT = "model"

@step
def train_step(learning_rate: float) -> Annotated[ClassifierMixin, MODEL_OUTPUT]:
    """Train a model with the given learning‑rate."""
    # <your training code goes here>
    ...
```

---

## Step 2 Create a fan‑out / fan‑in pipeline

Next, wire several instances of the same `train_step` into a pipeline, each with a different hyper‑parameter.  Afterwards, use a *selection* step that takes all models as input and decides which one is best.

```python
from zenml import pipeline
from zenml import get_step_context, step
from zenml.client import Client

@step
def selection_step(step_prefix: str, output_name: str):
    """Pick the best model among all training steps."""
    run = Client().get_pipeline_run(get_step_context().pipeline_run.name)
    trained_models = {}
    for step_name, step_info in run.steps.items():
        if step_name.startswith(step_prefix):
            model = step_info.outputs[output_name][0].load()
            lr = step_info.config.parameters["learning_rate"]
            trained_models[lr] = model

    # <evaluate and select your favorite model here>

@pipeline
def hp_tuning_pipeline(step_count: int = 4):
    after = []
    for i in range(step_count):
        train_step(learning_rate=i * 0.0001, id=f"train_step_{i}")
        after.append(f"train_step_{i}")

    selection_step(step_prefix="train_step_", output_name=MODEL_OUTPUT, after=after)
```

{% hint style="warning" %}
Currently ZenML doesn't allow passing a *variable* number of inputs into a step.  The workaround shown above queries the artifacts after the fact via the `Client`.
{% endhint %}

---

## Step 3 Run the pipeline

```python
if __name__ == "__main__":
    hp_tuning_pipeline(step_count=4)()
```

While the pipeline is running you can:

* follow the logs in your terminal
* open the ZenML dashboard and watch the DAG execute

---

## Step 4 Inspect results

Once the run is finished you can programmatically analyze which hyper‑parameter performed best or load the chosen model:

```python
from zenml.client import Client

run = Client().get_pipeline("hp_tuning_pipeline").last_run
best_model = run.steps["selection_step"].outputs["best_model"].load()
```

For a deeper exploration of how to query past pipeline runs, see the [Inspecting past pipeline runs](fetching-pipelines.md) tutorial.

---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


## Next steps

* Replace the simple grid‑search with a more sophisticated tuner (e.g. `sklearn.model_selection.GridSearchCV` or [Optuna](https://optuna.org/)).
* Serve the winning model via a [Model Deployer](https://docs.zenml.io/stacks/model-deployers) to serve it right away.
* Move the pipeline to a [remote orchestrator](https://docs.zenml.io/stacks/orchestrators) to scale out the search.