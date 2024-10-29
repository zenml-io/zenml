---
description: Running a hyperparameter tuning trial with ZenML.
---

# Hyperparameter tuning

{% hint style="warning" %}
Hyperparameter tuning is not yet a first-class citizen in ZenML, but it is [(high up) on our roadmap of features](https://zenml.featureos.app/p/enable-hyper-parameter-tuning) and will likely receive first-class ZenML support soon. In the meanwhile, the following example shows how hyperparameter tuning can currently be implemented within a ZenML run.
{% endhint %}

A basic iteration through a number of hyperparameters can be achieved with ZenML by using a simple pipeline like this:

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

This is an implementation of a basic grid search (across a single dimension) that would allow for a different learning rate to be used across the same `train_step`. Once that step has been run for all the different learning rates, the `select_model_step` finds which hyperparameters gave the best results or performance.

<details>

<summary>See it in action with the E2E example</summary>

_To set up the local environment used below, follow the recommendations from the_ [_Project templates_](../setting-up-a-project-repository/using-project-templates.md)_._

In [`pipelines/training.py`](../../../../examples/e2e/pipelines/training.py), you will find a training pipeline with a `Hyperparameter tuning stage` section. It contains a `for` loop that runs the `hp_tuning_single_search` over the configured model search spaces, followed by the `hp_tuning_select_best_model` being executed after all search steps are completed. As a result, we are getting `best_model_config` to be used to train the best possible model later on.

```python
...
########## Hyperparameter tuning stage ##########
after = []
search_steps_prefix = "hp_tuning_search_"
for i, model_search_configuration in enumerate(
    MetaConfig.model_search_space
):
    step_name = f"{search_steps_prefix}{i}"
    hp_tuning_single_search(
        model_metadata=ExternalArtifact(
            value=model_search_configuration,
        ),
        id=step_name,
        dataset_trn=dataset_trn,
        dataset_tst=dataset_tst,
        target=target,
    )
    after.append(step_name)
best_model_config = hp_tuning_select_best_model(
    search_steps_prefix=search_steps_prefix, after=after
)
...
```

</details>

The main challenge of this implementation is that it is currently not possible to pass a variable number of artifacts into a step programmatically, so the `select_model_step` needs to query all artifacts produced by the previous steps via the ZenML Client instead:

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

<details>

<summary>See it in action with the E2E example</summary>

_To set up the local environment used below, follow the recommendations from the_ [_Project templates_](../setting-up-a-project-repository/using-project-templates.md)_._

In the `steps/hp_tuning` folder, you will find two step files, which can be used as a starting point for building your own hyperparameter search tailored specifically to your use case:

* [`hp_tuning_single_search(...)`](../../../../examples/e2e/steps/hp_tuning/hp_tuning_single_search.py) is performing a randomized search for the best model hyperparameters in a configured space.
* [`hp_tuning_select_best_model(...)`](../../../../examples/e2e/steps/hp_tuning/hp_tuning_select_best_model.py) is searching for the best hyperparameters, looping other results of previous random searches to find the best model according to a defined metric.

</details>

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
