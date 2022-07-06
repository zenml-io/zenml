---
description: How to use the functional and class-based APIs for ZenML steps and pipelines.
---

In ZenML there are two different ways how you can define pipelines or steps.
What you have seen in the previous sections is the **Functional API**,
where steps and pipelines are defined as simple Python functions with a
`@step` or `@pipeline` decorator respectively.
This is the API that is used primarily throughout the ZenML docs and examples.

Alternatively, you can also define steps and pipelines using the 
**Class-Based API** by creating Python classes that subclass ZenML's abstract
base classes `BaseStep` and `BasePipeline` directly.
Internally, both APIs will result in similar definitions, so it is
entirely up to you which API to use.

In the following, we will compare the two APIs using the code from the previous
section on [Runtime Configuration](./runtime-configuration.md):

## Creating Steps

In order to create a step with the class-based API, you will need to create a
subclass of the `BaseStep` and implement its `entrypoint()` method, which 
contains the logic of the step.

{% tabs %}
{% tab title="Class-based API" %}
```python
from zenml.steps import BaseStep, BaseStepConfig, Output


class SecondStepConfig(BaseStepConfig):
    multiplier: int = 4
 
class SecondStep(BaseStep):
    def entrypoint(
        self,
        config: SecondStepConfig,
        input_int: int,
        input_float: float
    ) -> Output(output_int=int, output_float=float):
        return config.multiplier * input_int, config.multiplier * input_float
```
{% endtab %}
{% tab title="Functional API" %}
```python
from zenml.steps import BaseStepConfig, step, Output


class SecondStepConfig(BaseStepConfig):
    multiplier: int = 4

@step
def my_second_step(
    config: SecondStepConfig,
    input_int: int,
    input_float: float
) -> Output(output_int=int, output_float=float):
    return config.multiplier * input_int, config.multiplier * input_float
```
{% endtab %}
{% endtabs %}


### Using decorators to enhance BaseStep subclasses

ZenML allows you to easily add functionality like automated experiment tracking
to your steps. Similar to the functional API, you can do this in the
class-based API by adding a decorator to your `BaseStep` subclass:

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

## Creating Pipelines

Similar to creating steps, you can create a pipeline with the class-based API
by subclassing `BasePipeline` and implementing its `connect()` method:

{% tabs %}
{% tab title="Class-based API" %}
```python
from zenml.pipelines import BasePipeline


class FirstPipeline(BasePipeline):
    def connect(self, step_1, step_2):
        output_1, output_2 = step_1()
        step_2(output_1, output_2)

FirstPipeline(
    step_1=my_first_step(),
    step_2=SecondStep(SecondStepConfig(multiplier=3))
).run()
```
{% endtab %}
{% tab title="Functional API" %}
```python
from zenml.pipelines import pipeline


@pipeline
def first_pipeline(step_1, step_2):
    output_1, output_2 = step_1()
    step_2(output_1, output_2)

first_pipeline(
    step_1=my_first_step(),
    step_2=SecondStep(SecondStepConfig(multiplier=3))
).run()
```
{% endtab %}
{% endtabs %}

As you saw in the example above, you can even mix and match the two APIs.
Choose whichever style feels most natural to you!
