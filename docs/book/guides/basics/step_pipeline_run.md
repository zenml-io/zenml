---
description: Create steps and pipelines
---

# Create steps

Steps are the atomic components of a ZenML pipeline. Each step is defined by its inputs, the logic it applies and its 
outputs. Here is a very simple example of such a step:

{% tabs %}
{% tab title="Single Output" %}
```python
from zenml.steps import step

@step
def my_first_step() -> int:
    """Step that returns a pre-defined integer"""
    return 7
```
{% endtab %}

{% tab title="Multiple Outputs" %}
```python
from zenml.steps import step, Output

@step
def my_first_step() -> Output(output_int=int, output_float=float):
    """Step that returns a pre-defined integer and float"""
    return 7, 0.1
```

As this step has multiple outputs, we need to use the `zenml.steps.step_output.Output` class to indicate the names 
of each output.
{% endtab %}
{% endtabs %}

Let's come up with a second step that consumes the output of our first step and performs some sort of transformation
on it. In this case, let's double the input.

```python
from zenml.steps import step

@step
def my_second_step(input_int: int) -> int:
    """Step that doubles the input"""
    return 2 * input_int
```

Now we can go ahead and create a pipeline with our two steps to make sure they work.

# Define the Pipeline

Here we define the pipeline. This is done implementation agnostic by simply routing outputs through the 
steps within the pipeline. You can think of this as a recipe for how we want data to flow through our steps.

```python
from zenml.pipelines import pipeline

@pipeline
def first_pipeline(
    step_1,
    step_2
):
    output_1 = step_1
    step_2(output_1)
```


# Instantiate and run your Pipeline

With your pipeline recipe in hand you can now specify which particular steps implement the pipeline. And with that, you
are ready to run:

```python
first_pipeline(step_1=my_first_step(), step_2=my_second_step()).run()
```


# Putting it all together

This is what it looks like when you put it all together.

```python
from zenml.steps import step
from zenml.pipelines import pipeline

@step
def my_first_step() -> int:
    """Step that returns a pre-defined integer"""
    return 7


@step
def my_second_step(input_int: int) -> int:
    """Step that doubles the input"""
    return 2 * input_int


@pipeline
def first_pipeline(
    step_1,
    step_2
):
    output_1 = step_1
    step_2(output_1)

first_pipeline(step_1=my_first_step(), step_2=my_second_step()).run()
```
