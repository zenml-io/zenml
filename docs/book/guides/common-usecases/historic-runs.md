# Fetching historic runs

## The need to fetch historic runs

## Utilizing `StepContext`

This example builds on the showcases how to use a `StepContext` to query the metadata store while running a step.
We use this to evaluate all models of past training pipeline runs and store the currently best model. 
In our inference pipeline we could then easily query the metadata store the fetch the best performing model.

```python
import numpy as np
from sklearn.base import ClassifierMixin
from zenml.pipelines import pipeline
from zenml.steps import Output, StepContext, step

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
```