---
description: Use Step Fixtures to Access the Stack from within a Step.
---

# Step Fixtures

In general, when defining steps, you usually can only supply inputs that have
been output by previous steps. However, there are two exceptions:

* An object which is a subclass of `BaseStepConfig`: This object is used to
pass run-time parameters to a pipeline run. It can be used to send parameters
to a step that are not artifacts. You learned about this one already in the
section on [Runtime Configuration](../steps-pipelines/runtime-configuration.md).
* A [Step Context](#step-contexts) object: This object gives access to the 
active stack materializers, and special integration-specific libraries.

These two types of special parameters are comparable to 
[Pytest fixtures](https://docs.pytest.org/en/6.2.x/fixture.html), hence we call
them **Step Fixtures** at ZenML.

To use step fixtures in your steps, just pass a parameter with the right type
hint and ZenML will automatically recognize it.

```python
from zenml.steps import step, BaseStepConfig, StepContext


class SubClassBaseStepConfig(BaseStepConfig):
    ...


@step
def my_step(
    config: SubClassBaseStepConfig,  # must be subclass of `BaseStepConfig`
    context: StepContext,  # must be of class `StepContext`
    artifact: str,  # all other parameters are artifacts from upstream steps
):
    ...
```

{% hint style="info" %}
The name of the argument can be anything, only the type hint is important. 
I.e., you don't necessarily need to call your fixtures `config` or `context`.
{% endhint %}

## Step Contexts

The `StepContext` provides additional context inside a step function. It can be
used to access artifacts, materializers, stack components, and more directly 
from within the step.

### Defining Steps with Step Contexts

Unlike `BaseStepConfig`, you do not need to create a `StepContext` object
yourself and pass it when creating the step. As long as you specify a parameter
of type `StepContext` in the signature of your step function or class, ZenML 
will automatically create the `StepContext` and take care of passing it to your
step at runtime.

{% hint style="info" %}
When using a `StepContext` inside a step, ZenML disables caching for this step by
default as the context provides access to external resources which might
influence the result of your step execution. To enable caching anyway, 
explicitly enable it in the `@step` decorator with `@step(enable_cache=True)`
or when initializing your custom step class.
{% endhint %}

### Using Step Contexts

Within a step, there are many things that you can use the `StepContext` object
for. For example, to access materializers, artifact locations, etc:

```python
from zenml.steps import step, StepContext


@step
def my_step(context: StepContext):
    context.get_output_materializer()  # Returns a materializer for a given step output.
    context.get_output_artifact_uri()  # Returns the URI for a given step output.
    context.metadata_store  # Get access to the metadata store.
```

{% hint style="info" %}
See the [API reference](https://apidocs.zenml.io/latest/api_docs/steps/) for
more information on which attributes and methods the `StepContext` provides.
{% endhint %}



## Fetching Historic Runs

One of the most common usecases of the `StepContext` is to query the metadata store
for a list of all previous pipeline runs, e.g., in order to compare a newly
trained model to models trained in previous runs, or to fetch artifacts created
in different pipelines.

As an example, see the following step that uses the `StepContext` to query the
metadata store while running a step, which we use to evaluate all models of
past training pipeline runs and to store the current best model, which we could
then automatically deploy or use for inference in another pipeline.

```python
from zenml.steps import step, StepContext


@step
def find_best_model(context: StepContext, test_acc: float) -> bool:
    """Step that finds if this run produced the highest `test_acc` ever"""
    highest_acc = 0

    # Inspect all past runs of `best_model_pipeline`.
    try:
        metadata_store = context.metadata_store
        prior_runs = metadata_store.get_pipeline("best_model_pipeline").runs
    except KeyError:
        print("No prior runs found.")
        prior_runs = []

    # Find the highest accuracy produced in a prior run.
    for run in prior_runs:
        # get the output of the second step
        prior_test_acc = run.get_step("evaluator").output.read()
        if prior_test_acc > highest_acc:
            highest_acc = prior_test_acc

    # Check whether the current run produced the highest accuracy or not.
    if test_acc >= highest_acc:
        print(f"This run produced the highest test accuracy: {test_acc}.")
        return True
    print(
        f"This run produced test accuracy {test_acc}, which is not the highest."
        f"\nThe highest previous test accuracy was {highest_acc}."
    )
    return False
```

### Full Code Example

<details>
    <summary>Code Example for Fetching Historic Runs</summary>

```python
import numpy as np
from sklearn.base import ClassifierMixin
from sklearn.svm import SVC

from zenml.integrations.sklearn.helpers.digits import get_digits
from zenml.pipelines import pipeline
from zenml.steps import BaseStepConfig, Output, StepContext, step


@step
def load_digits() -> Output(
    X_train=np.ndarray, X_test=np.ndarray, y_train=np.ndarray, y_test=np.ndarray
):
    """Loads the digits dataset as normal numpy arrays."""
    X_train, X_test, y_train, y_test = get_digits()
    return X_train, X_test, y_train, y_test


class SVCTrainerStepConfig(BaseStepConfig):
    """Trainer params"""

    gamma: float = 0.001


@step()
def svc_trainer(
    config: SVCTrainerStepConfig,
    X_train: np.ndarray,
    y_train: np.ndarray,
) -> ClassifierMixin:
    """Train a sklearn SVC classifier."""
    model = SVC(gamma=config.gamma)
    model.fit(X_train, y_train)
    return model


@step
def evaluator(
    X_test: np.ndarray,
    y_test: np.ndarray,
    model: ClassifierMixin,
) -> float:
    """Calculate the accuracy on the test set"""
    test_acc = model.score(X_test, y_test)
    print(f"Test accuracy: {test_acc}")
    return test_acc


@step
def find_best_model(context: StepContext, test_acc: float) -> bool:
    """Step that finds if this run produced the highest `test_acc` ever"""
    highest_acc = 0

    # Inspect all past runs of `best_model_pipeline`.
    try:
        metadata_store = context.metadata_store
        prior_runs = metadata_store.get_pipeline("best_model_pipeline").runs
    except KeyError:
        print("No prior runs found.")
        prior_runs = []

    # Find the highest accuracy produced in a prior run.
    for run in prior_runs:
        # get the output of the second step
        prior_test_acc = run.get_step("evaluator").output.read()
        if prior_test_acc > highest_acc:
            highest_acc = prior_test_acc

    # Check whether the current run produced the highest accuracy or not.
    if test_acc >= highest_acc:
        print(f"This run produced the highest test accuracy: {test_acc}.")
        return True
    print(
        f"This run produced test accuracy {test_acc}, which is not the highest."
        f"\nThe highest previous test accuracy was {highest_acc}."
    )
    return False


@pipeline
def best_model_pipeline(importer, trainer, evaluator, find_best_model):
    X_train, X_test, y_train, y_test = importer()
    model = trainer(X_train, y_train)
    test_acc = evaluator(X_test, y_test, model)
    find_best_model(test_acc)


for gamma in (0.01, 0.001, 0.0001):

    best_model_pipeline(
        importer=load_digits(),
        trainer=svc_trainer(SVCTrainerStepConfig(gamma=gamma)),
        evaluator=evaluator(),
        find_best_model=find_best_model(),
    ).run()

```

#### Expected Output

```shell
...
No prior runs found.
This run produced the highest test accuracy: 0.6974416017797553.
...
This run produced the highest test accuracy: 0.9688542825361512.
...
This run produced test accuracy 0.9399332591768632, which is not the highest.
The highest previous test accuracy was 0.9688542825361512.
...
```

</details>
