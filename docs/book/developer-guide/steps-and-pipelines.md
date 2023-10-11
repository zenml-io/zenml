---
description: Create Steps, Build a Pipeline and Run it.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To check the latest version please [visit https://docs.zenml.io](https://docs.zenml.io)
{% endhint %}


# Steps & Pipelines

## Step

Steps are the atomic components of a ZenML pipeline. Each step is defined by its
inputs, the logic it applies and its outputs. Here is a very simple example of
such a step:

```python
from zenml.steps import step, Output


@step
def my_first_step() -> Output(output_int=int, output_float=float):
    """Step that returns a pre-defined integer and float"""
    return 7, 0.1
```

As this step has multiple outputs, we need to use
the `zenml.steps.step_output.Output` class to indicate the names
of each output. These names can be used to directly access an output within the
[post execution workflow](./post-execution-workflow.md).

Let's come up with a second step that consumes the output of our first step and
performs some sort of transformation
on it. In this case, let's double the input.

```python
from zenml.steps import step, Output


@step
def my_second_step(input_int: int, input_float: float
                   ) -> Output(output_int=int, output_float=float):
    """Step that doubles the inputs"""
    return 2 * input_int, 2 * input_float
```

Now we can go ahead and create a pipeline with our two steps to make sure they
work.

{% hint style="info" %}
In case you want to run the step function outside the context of a ZenML 
pipeline, all you need to do is call the `.entrypoint()` method with the same
input signature. For example:

```python
my_second_step.entrypoint(input_int=1, input_float=0.9)
```
{% endhint %}

## Pipeline

Here we define the pipeline. This is done agnostic of implementation by simply
routing outputs through the
steps within the pipeline. You can think of this as a recipe for how we want
data to flow through our steps.

```python
from zenml.pipelines import pipeline


@pipeline
def first_pipeline(
        step_1,
        step_2
):
    output_1, output_2 = step_1()
    step_2(output_1, output_2)
```

### Instantiate and run your Pipeline

With your pipeline recipe in hand you can now specify which concrete step
implementations are used. And with that, you
are ready to run:

```python
first_pipeline(step_1=my_first_step(), step_2=my_second_step()).run()
```

You should see the following output on your command line:

```shell
Creating run for pipeline: `first_pipeline`
Cache disabled for pipeline `first_pipeline`
Using stack `default` to run pipeline `first_pipeline`
Step `my_first_step` has started.
Step `my_first_step` has finished in 0.049s.
Step `my_second_step` has started.
Step `my_second_step` has finished in 0.067s.
Pipeline run `first_pipeline-20_Apr_22-16_07_14_577771` has finished in 0.128s.
```

You'll learn how to inspect the finished run within the chapter on
our [Post Execution Workflow](./post-execution-workflow.md).

#### Summary in Code

<details>
    <summary>Code Example for this Section</summary>

```python
from zenml.steps import step, Output
from zenml.pipelines import pipeline


@step
def my_first_step() -> Output(output_int=int, output_float=float):
    """Step that returns a pre-defined integer and float"""
    return 7, 0.1


@step
def my_second_step(input_int: int, input_float: float
                   ) -> Output(output_int=int, output_float=float):
    """Step that doubles the inputs"""
    return 2 * input_int, 2 * input_float


@pipeline
def first_pipeline(
        step_1,
        step_2
):
    output_1, output_2 = step_1()
    step_2(output_1, output_2)


first_pipeline(step_1=my_first_step(), step_2=my_second_step()).run()
```

</details>

### Give each pipeline run a name

When running a pipeline by calling `my_pipeline.run()`, ZenML uses the current
date and time as the name for the
pipeline run. In order to change the name for a run, simply pass it as a
parameter to the `run()` function:

```python
first_pipeline_instance.run(run_name="custom_pipeline_run_name")
```

{% hint style="warning" %}
Pipeline run names must be unique, so make sure to compute it dynamically if you
plan to run your pipeline multiple
times.
{% endhint %}

Once the pipeline run is finished we can easily access this specific run during
our post-execution workflow:

```python
from zenml.repository import Repository

repo = Repository()
pipeline = repo.get_pipeline(pipeline_name="first_pipeline")
run = pipeline.get_run("custom_pipeline_run_name")
```

#### Summary in Code

<details>
    <summary>Code Example for this Section</summary>

```python
from zenml.steps import step, Output, BaseStepConfig
from zenml.pipelines import pipeline


@step
def my_first_step() -> Output(output_int=int, output_float=float):
    """Step that returns a pre-defined integer and float"""
    return 7, 0.1


class SecondStepConfig(BaseStepConfig):
    """Trainer params"""
    multiplier: int = 4


@step
def my_second_step(config: SecondStepConfig, input_int: int,
                   input_float: float
                   ) -> Output(output_int=int, output_float=float):
    """Step that multiply the inputs"""
    return config.multiplier * input_int, config.multiplier * input_float


@pipeline
def first_pipeline(
        step_1,
        step_2
):
    output_1, output_2 = step_1()
    step_2(output_1, output_2)


# Set configuration when executing
first_pipeline(step_1=my_first_step(),
               step_2=my_second_step(SecondStepConfig(multiplier=3))
               ).run(run_name="custom_pipeline_run_name")

# Set configuration  based on yml
first_pipeline(step_1=my_first_step(),
               step_2=my_second_step()
               ).with_config("config.yml").run()
```

With config.yml looking like this

```yaml
steps:
  step_2:
    parameters:
      multiplier: 3
```

</details>