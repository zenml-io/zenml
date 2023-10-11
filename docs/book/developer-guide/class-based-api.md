---
description: Use the class-based API for Steps and Pipelines.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To check the latest version please [visit https://docs.zenml.io](https://docs.zenml.io)
{% endhint %}


The class-based ZenML API is defined by the base classes BaseStep and BasePipeline. You'll be subclassing these instead 
of using the `@step` and `@pipeline` decorators that you have used in the previous sections. These interfaces allow our 
users to maintain a higher level of control while they are creating a step definition and using it within the context of 
a pipeline.

We'll be using the code for the [Runtime Configuration](./runtime-configuration.md) as a point of comparison.

### Subclassing the BaseStep

In order to create a step, you will need to create a subclass of the `BaseStep` and implement
its `entrypoint()` method. This entrypoint contains the logic of the step.

{% tabs %}
{% tab title="Class-based API" %}
```python
from zenml.steps import BaseStep, BaseStepConfig, Output

class SecondStepConfig(BaseStepConfig):
    """Trainer params"""
    multiplier: int = 4

    
class SecondStep(BaseStep):
    def entrypoint(
            self,
            config: SecondStepConfig,
            input_int: int,
            input_float: float) -> Output(output_int=int, output_float=float):
        """Step that multiply the inputs"""
        return config.multiplier * input_int, config.multiplier * input_float
```
{% endtab %}
{% tab title="Functional API" %}
```python
from zenml.steps import BaseStepConfig, step, Output
class SecondStepConfig(BaseStepConfig):
    """Trainer params"""
    multiplier: int = 4

@step
def my_second_step(config: SecondStepConfig, input_int: int,
                   input_float: float
                   ) -> Output(output_int=int, output_float=float):
    """Step that multiply the inputs"""
    return config.multiplier * input_int, config.multiplier * input_float
```
{% endtab %}
{% endtabs %}


### Use decorators to enhance your BaseStep subclasses

ZenML allows you to easily add functionality like automated experiment tracking to your steps.
To do so with the class-based API, simply decorate your `BaseStep` subclass as follows:

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

Check out our [MLflow](https://github.com/zenml-io/zenml/tree/main/examples/mlflow_tracking), 
[Wandb](https://github.com/zenml-io/zenml/tree/main/examples/wandb_tracking) and 
[whylogs](https://github.com/zenml-io/zenml/tree/main/examples/whylogs_data_profiling) 
examples for more information on how to use the specific decorators.

### Subclassing the BasePipeline

{% tabs %}
{% tab title="Class-based API" %}
```python
from zenml.steps import BaseStep
from zenml.pipelines import BasePipeline


class FirstPipeline(BasePipeline):
    """Pipeline to show off the class-based API"""

    def connect(self,
                step_1: BaseStep,
                step_2: BaseStep) -> None:
        output_1, output_2 = step_1()
        step_2(output_1, output_2)

FirstPipeline(step_1=my_first_step(),
              step_2=SecondStep(SecondStepConfig(multiplier=3))).run()
```
{% endtab %}
{% tab title="Functional API" %}
```python
from zenml.pipelines import pipeline

@pipeline
def first_pipeline(
        step_1,
        step_2
):
    output_1, output_2 = step_1()
    step_2(output_1, output_2)

first_pipeline(step_1=my_first_step(),
               step_2=my_second_step(SecondStepConfig(multiplier=3))
               ).run()
```
{% endtab %}
{% endtabs %}

You can also mix and match the two APIs to your hearts content. Check out the full Code example below to see how.


### Summary in Code

<details>
    <summary>Code Example for this Section</summary>

```python
from zenml.steps import step, Output, BaseStepConfig, BaseStep
from zenml.pipelines import BasePipeline

@step
def my_first_step() -> Output(output_int=int, output_float=float):
    """Step that returns a pre-defined integer and float"""
    return 7, 0.1

class SecondStepConfig(BaseStepConfig):
    """Trainer params"""
    multiplier: int = 4

class SecondStep(BaseStep):
    def entrypoint(
            self,
            config: SecondStepConfig,
            input_int: int,
            input_float: float) -> Output(output_int=int,
                                          output_float=float):
        """Step that multiply the inputs"""
        return config.multiplier * input_int, config.multiplier * input_float

class FirstPipeline(BasePipeline):
    """Pipeline to show off the class-based API"""

    def connect(self,
                step_1: BaseStep,
                step_2: BaseStep) -> None:
        output_1, output_2 = step_1()
        step_2(output_1, output_2)

FirstPipeline(step_1=my_first_step(),
              step_2=SecondStep(SecondStepConfig(multiplier=3))).run()
```
</details>
