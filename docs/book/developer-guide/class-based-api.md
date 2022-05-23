---
description: Use the class-based API for Steps and Pipelines.
---

# Class-based API

The class-based ZenML API is defined by the base classes BaseStep and BasePipeline. You'll be subclassing these instead 
of using the `@step` and `@pipeline` decorators that you have used in the previous sections. These interfaces allow our 
users to maintain a higher level of control while they are creating a step definition and using it within the context of 
a pipeline.

We'll be using the code for the [Chapter on Runtime Configuration](#configure-at-runtime) as a point of comparison.

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
