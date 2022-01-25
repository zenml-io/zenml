---
description: All code in this guide can be found [here](https://github.com/zenml-io/zenml/tree/main/examples/fetch_historical_runs).
---

# Fetching historic runs



## The need to fetch historic runs

Sometimes, it is necessary to fetch information from previous runs in order to make a decision within a currently 
executing step. Examples of this:

* Fetch the best model evaluation results from history to decide whether to deploy a newly trained model.
* Fetching best model out of a list of trained models.
* Fetching the latest model before running an inference.

And so on.

## Utilizing `StepContext`

ZenML allows users to fetch historical parameters and artifacts using the `StepContext` 
[fixture](../../features/step-fixtures.md).

As an example, see below a step that uses the `StepContext` to query the metadata store while running a step.
We use this to evaluate all models of past training pipeline runs and store the current best model. 
In our inference pipeline, we could then easily query the metadata store the fetch the best performing model.

```python
@step
def evaluate_and_store_best_model(
    context: StepContext,
    X_test: np.ndarray,
    y_test: np.ndarray,
    model: ClassifierMixin,
) -> ClassifierMixin:
    """Evaluate all models and return the best one."""
    best_accuracy = model.score(X_test, y_test)
    best_model = model

    pipeline_runs = context.metadata_store.get_pipeline("mnist_pipeline").runs
    for run in pipeline_runs:
        # get the trained model of all pipeline runs
        model = run.get_step("trainer").output.read()
        accuracy = model.score(X_test, y_test)
        if accuracy > best_accuracy:
            # if the model accuracy is better than our currently best model,
            # store it
            best_accuracy = accuracy
            best_model = model

    print(f"Best test accuracy: {best_accuracy}")
    return best_model
```

And that's it!