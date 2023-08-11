---
description: Running a hyperparameter tuning trial with ZenML.
---

# Hyperparameter Tuning

{% hint style="warning" %}
Hyperparameter tuning is not yet a first-class citizen in ZenML, but it is 
[(high up) on our roadmap of features](https://zenml.featureos.app/p/enable-hyper-parameter-tuning) 
and will likely receive first-class ZenML support soon. In the meanwhile, the
following example shows how hyperparameter tuning can currently be implemented
within a ZenML run.
{% endhint %}

A basic iteration through a number of hyperparameters can be achieved with 
ZenML by using a simple pipeline like this:

```python
@pipeline
def my_pipeline(step_count: int) -> None:
    data = load_data_step()
    after = []
    for i in range(step_count):
        train_step(data, learning_rate=i * 0.0001, name=f"train_step_{i}")
        after.append(f"train_step_{i}")
    model = select_model_step(..., after=after)
```

This is an implementation of a basic grid search (across a single dimension) 
that would allow for a different learning rate to be used across the same
`train_step`. Once that step has been run for all the different learning rates, 
the `select_model_step` finds which hyperparameters gave the best results or 
performance.

The main challenge of this implementation is that it is currently not possible 
to pass a variable number of artifacts into a step programmatically, so the
`select_model_step` needs to query all artifacts produced by the previous steps 
via the ZenML Client instead:

```python
from zenml import step, get_step_context
from zenml.client import Client

@step
def select_model_step():
    run_name = get_step_context().pipeline_run.name
    run = Client().get_pipeline_run(run_name)

    # Fetch all models trained by a 'train_step' before
    trained_models_by_lr = {}
    for step_name, step in run.steps.items():
        if step_name.startswith("train_step"):
            for output_name, output in step.outputs.items():
                if output_name == "<NAME_OF_MODEL_OUTPUT_IN_TRAIN_STEP>":
                    model = output.load()
                    lr = step.config.parameters["learning_rate"]
                    trained_models_by_lr[lr] = model
    
    # Evaluate the models to find the best one
    for lr, model in trained_models_by_lr.items():
        ...
```

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
