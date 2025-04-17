---
description: Running a hyperparameter tuning trial with ZenML.
icon: itunes-note
---

# Hyper-parameter tuning

A basic iteration through a number of hyperparameters can be achieved with\
ZenML by using a simple pipeline. The following example showcases an\
implementation of a basic grid search (across a single dimension)\
that would allow for a different learning rate to be used across the\
same `train_step`. Once that step has been run for all the different\
learning rates, the `selection_step` finds which hyperparameters gave the\
best results or performance. It utilizes the [fan-in, fan-out method of\
building a pipeline.](../../how-to/pipeline-development/build-pipelines/fan-in-fan-out.md)

```python
from typing import Annotated

from sklearn.base import ClassifierMixin

from zenml import step, pipeline, get_step_context
from zenml.client import Client

model_output_name = "my_model"


@step
def train_step(
    learning_rate: float
) -> Annotated[ClassifierMixin, model_output_name]:
    return ...  # Train a model with the learning rate and return it here. 


@step
def selection_step(step_prefix: str, output_name: str) -> None:
    run_name = get_step_context().pipeline_run.name
    run = Client().get_pipeline_run(run_name)

    trained_models_by_lr = {}
    for step_name, step_info in run.steps.items():
        if step_name.startswith(step_prefix):
            model = step_info.outputs[output_name][0].load()
            lr = step_info.config.parameters["learning_rate"]
            trained_models_by_lr[lr] = model

    for lr, model in trained_models_by_lr.items():
        ...  # Evaluate the models to find the best one


@pipeline
def my_pipeline(step_count: int) -> None:
    after = []
    for i in range(step_count):
        train_step(learning_rate=i * 0.0001, id=f"train_step_{i}")
        after.append(f"train_step_{i}")

    selection_step(
        step_prefix="train_step_",
        output_name=model_output_name,
        after=after
    )


my_pipeline(step_count=4)
```

{% hint style="warning" %}
The main challenge of this implementation is that it is currently not\
possible to pass a variable number of artifacts into a step programmatically,\
so the `selection_step` needs to query all artifacts produced by the previous\
steps via the ZenML Client instead.
{% endhint %}

{% hint style="info" %}
You can also see this in action with the [E2E example](https://github.com/zenml-io/zenml/tree/main/examples/e2e).

In the `steps/hp_tuning` folder, you will find two step files, that can be\
used as a starting point for building your own hyperparameter search tailored\
specifically to your use case:

* [`hp_tuning_single_search(...)`](https://github.com/zenml-io/zenml/blob/main/examples/e2e/steps/hp_tuning/hp_tuning_single_search.py) is performing a randomized search for the best model hyperparameters in a configured space.
* [`hp_tuning_select_best_model(...)`](https://github.com/zenml-io/zenml/blob/main/examples/e2e/steps/hp_tuning/hp_tuning_select_best_model.py) is searching for the best hyperparameters, looping other results of previous random searches to find the best model according to a defined metric.
{% endhint %}

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
