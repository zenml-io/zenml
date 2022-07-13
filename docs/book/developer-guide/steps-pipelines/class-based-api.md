---
description: How to use the functional and class-based APIs for ZenML steps and pipelines.
---

In ZenML there are two different ways how you can define pipelines or steps.
What you have seen in the previous sections is the **Functional API**,
where steps and pipelines are defined as Python functions with a
`@step` or `@pipeline` decorator respectively.
This is the API that is used primarily throughout the ZenML docs and examples.

Alternatively, you can also define steps and pipelines using the 
**Class-Based API** by creating Python classes that subclass ZenML's abstract
base classes `BaseStep` and `BasePipeline` directly.
Internally, both APIs will result in similar definitions, so it is
entirely up to you which API to use.

In the following, we will compare the two APIs using the code example from the
previous section on [Runtime Configuration](./runtime-configuration.md):

## Creating Steps

In order to create a step with the class-based API, you will need to create a
subclass of `zenml.steps.BaseStep` and implement its `entrypoint()` method to
perform the logic of the step.

{% tabs %}
{% tab title="Class-based API" %}
```python
import numpy as np
from sklearn.base import ClassifierMixin
from sklearn.svm import SVC

from zenml.steps import BaseStep, BaseStepConfig


class SVCTrainerStepConfig(BaseStepConfig):
    """Trainer params"""
    gamma: float = 0.001


class SVCTrainerStep(BaseStep):
    def entrypoint(
        self,
        config: SVCTrainerStepConfig,
        X_train: np.ndarray,
        y_train: np.ndarray,
    ) -> ClassifierMixin:
        """Train a sklearn SVC classifier."""
        model = SVC(gamma=config.gamma)
        model.fit(X_train, y_train)
        return model
```
{% endtab %}
{% tab title="Functional API" %}
```python
import numpy as np
from sklearn.base import ClassifierMixin
from sklearn.svm import SVC

from zenml.steps import step, BaseStepConfig


class SVCTrainerStepConfig(BaseStepConfig):
    """Trainer params"""
    gamma: float = 0.001


@step
def svc_trainer(
    config: SVCTrainerStepConfig,
    X_train: np.ndarray,
    y_train: np.ndarray,
) -> ClassifierMixin:
    """Train a sklearn SVC classifier."""
    model = SVC(gamma=config.gamma)
    model.fit(X_train, y_train)
    return model
```
{% endtab %}
{% endtabs %}

## Creating Pipelines

Similarly, you can define a pipeline with the class-based API
by subclassing `zenml.pipelines.BasePipeline` and implementing its `connect()`
method:

{% tabs %}
{% tab title="Class-based API" %}
```python
from zenml.pipelines import BasePipeline


class FirstPipeline(BasePipeline):
    def connect(self, step_1, step_2):
        X_train, X_test, y_train, y_test = step_1()
        step_2(X_train, y_train)


first_pipeline_instance = FirstPipeline(
    step_1=load_digits(),
    step_2=SVCTrainerStep(SVCTrainerStepConfig(gamma=0.01)),
)

first_pipeline_instance.run()

```
{% endtab %}
{% tab title="Functional API" %}
```python
from zenml.pipelines import pipeline


@pipeline
def first_pipeline(step_1, step_2):
    X_train, X_test, y_train, y_test = step_1()
    step_2(X_train, y_train)


first_pipeline_instance = first_pipeline(
    step_1=load_digits(),
    step_2=SVCTrainerStep(SVCTrainerStepConfig(gamma=0.01)),
)

first_pipeline_instance.run()
```
{% endtab %}
{% endtabs %}

As you saw in the example above, you can even mix and match the two APIs.
Choose whichever style feels most natural to you!

## Advanced Usage: Using decorators to enhance BaseStep subclasses

As you will learn later, ZenML has many [integrations](../../mlops_stacks/integrations.md)
that allow you to add functionality like automated experiment tracking to your steps.
Some of those integrations need to be initialized before they can be used, which
ZenML wraps using special `@enable_<INTEGRATION>` decorators.
Similar to the functional API, you can do this in the class-based API by 
adding a decorator to your `BaseStep` subclass:

{% tabs %}
{% tab title="Class-based API" %}
```python
from zenml.steps import BaseStep
from zenml.integrations.mlflow.mlflow_step_decorator import enable_mlflow


@enable_mlflow
class TFTrainer(BaseStep):
    def entrypoint(
        self,
        x_train: np.ndarray,
        y_train: np.ndarray,
    ) -> tf.keras.Model:
        mlflow.tensorflow.autolog()
        ...
```
{% endtab %}
{% tab title="Functional API" %}
```python
from zenml.steps import step
from zenml.integrations.mlflow.mlflow_step_decorator import enable_mlflow


@enable_mlflow
@step
def tf_trainer(
    X_train: np.ndarray,
    y_train: np.ndarray,
) -> tf.keras.Model:
    mlflow.tensorflow.autolog()
    ...
```
{% endtab %}
{% endtabs %}

Check out our [MLflow](https://github.com/zenml-io/zenml/tree/main/examples/mlflow_tracking), 
[Wandb](https://github.com/zenml-io/zenml/tree/main/examples/wandb_tracking) and 
[whylogs](https://github.com/zenml-io/zenml/tree/main/examples/whylogs_data_profiling) 
examples for more information on how to use the specific decorators.
