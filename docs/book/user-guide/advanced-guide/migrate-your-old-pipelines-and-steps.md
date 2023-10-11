---
description: Migrating your pipelines and steps to the new syntax.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Migrate your old pipelines and steps

ZenML version 0.40.0 introduced a new, more flexible syntax to define ZenML steps and pipelines. This page
contains code samples that show you how to upgrade your steps and pipelines to the new syntax.

{% hint style="warning" %}
Newer versions of ZenML still work with pipelines and steps defined using the old syntax,
but it is deprecated and will be removed in the future.
{% endhint %}

## Defining steps

```python
# Old: Subclass `BaseParameters` to define parameters for a step
from zenml.steps import step, BaseParameters
from zenml.pipelines import pipeline

class MyStepParameters(BaseParameters):
    param_1: int
    param_2: Optional[float] = None

@step
def my_step(params: MyStepParameters) -> None:
    ...

@pipeline
def my_pipeline(my_step):
    my_step()

step_instance = my_step(params=MyStepParameters(param_1=17))
pipeline_instance = my_pipeline(my_step=step_instance)

# New: Directly define the parameters as arguments of your step function.
# In case you still want to group your parameters in a separate class,
# you can subclass `pydantic.BaseModel` and use that as an argument of your
# step function
from zenml import pipeline, step

@step
def my_step(param_1: int, param_2: Optional[float] = None) -> None:
    ...

@pipeline
def my_pipeline():
    my_step(param_1=17)
```

Check out [this page](./configure-steps-pipelines.md#parameters-for-your-steps)
for more information on how to parameterize your steps.

## Calling a step outside of a pipeline

```python
# Old: Call `step.entrypoint(...)`
from zenml.steps import step

def my_step() -> None:
    ...

my_step.entrypoint()

# New: Call the step directly `step(...)`
from zenml import step

def my_step() -> None:
    ...

my_step()
```

## Defining pipelines

```python
# Old: The pipeline function gets steps as inputs and calls
# the passed steps
from zenml.pipelines import pipeline

@pipeline
def my_pipeline(my_step):
    my_step()

# New: The pipeline function calls the step directly
from zenml import pipeline, step

@step
def my_step() -> None:
    ...

@pipeline
def my_pipeline():
    my_step()
```

## Configuring pipelines

```python
# Old: Create an instance of the pipeline and then call `pipeline_instance.configure(...)`
from zenml.pipelines import pipeline
from zenml.steps import step

def my_step() -> None:
    ...

@pipeline
def my_pipeline(my_step):
    my_step()

pipeline_instance = my_pipeline(my_step=my_step())
pipeline_instance.configure(enable_cache=False)

# New: Call the `with_options(...)` method on the pipeline
from zenml import pipeline, step

@step
def my_step() -> None:
    ...

@pipeline
def my_pipeline():
    my_step()

my_pipeline = my_pipeline.with_options(enable_cache=False)
```

## Running pipelines

```python
# Old: Create an instance of the pipeline and then call `pipeline_instance.run(...)`
from zenml.pipelines import pipeline
from zenml.steps import step

def my_step() -> None:
    ...

@pipeline
def my_pipeline(my_step):
    my_step()

pipeline_instance = my_pipeline(my_step=my_step())
pipeline_instance.run(...)

# New: Call the pipeline
from zenml import pipeline, step

@step
def my_step() -> None:
    ...

@pipeline
def my_pipeline():
    my_step()

my_pipeline()
```

## Scheduling pipelines

```python
# Old: Create an instance of the pipeline and then call `pipeline_instance.run(schedule=...)`
from zenml.pipelines import pipeline, Schedule
from zenml.steps import step

def my_step() -> None:
    ...

@pipeline
def my_pipeline(my_step):
    my_step()

schedule = Schedule(...)
pipeline_instance = my_pipeline(my_step=my_step())
pipeline_instance.run(schedule=schedule)

# New: Set the schedule using the `pipeline.with_options(...)` method and then run it
from zenml.pipelines import Schedule
from zenml import pipeline, step

@step
def my_step() -> None:
    ...

@pipeline
def my_pipeline():
    my_step()

schedule = Schedule(...)
my_pipeline = my_pipeline.with_options(schedule=schedule)
my_pipeline()
```

Check out [this page](./schedule-pipeline-runs.md)
for more information on how to schedule your pipelines.

## Controlling the step execution order

```python
# Old: Use the `step.after(...)` method to define upstream steps
from zenml.pipelines import pipeline

@pipeline
def my_pipeline(step_1, step_2, step_3):
    step_1()
    step_2()
    step_3()
    step_3.after(step_1)
    step_3.after(step_2)

# New: Pass the upstream steps for the `after` argument
# when calling a step
from zenml import pipeline

@pipeline
def my_pipeline():
    step_1()
    step_2()
    step_3(after=["step_1", "step_2"])
```

Check out [this page](./configure-steps-pipelines.md#control-the-execution-order)
for more information on how to control the step execution order.


<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
