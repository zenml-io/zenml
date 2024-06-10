---
description: How to migrate your ZenML pipelines and steps from version <=0.39.1 to 0.41.0.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Migration guide 0.39.1 → 0.41.0

ZenML versions 0.40.0 to 0.41.0 introduced a new and more flexible syntax to define ZenML steps and pipelines. This page contains code samples that show you how to upgrade your steps and pipelines to the new syntax.

{% hint style="warning" %}
Newer versions of ZenML still work with pipelines and steps defined using the old syntax, but the old syntax is deprecated and will be removed in the future.
{% endhint %}

## Overview

{% tabs %}
{% tab title="Old Syntax" %}
```python
from typing import Optional

from zenml.steps import BaseParameters, Output, StepContext, step
from zenml.pipelines import pipeline

# Define a Step
class MyStepParameters(BaseParameters):
    param_1: int
    param_2: Optional[float] = None

@step
def my_step(
    params: MyStepParameters, context: StepContext,
) -> Output(int_output=int, str_output=str):
    result = int(params.param_1 * (params.param_2 or 1))
    result_uri = context.get_output_artifact_uri()
    return result, result_uri

# Run the Step separately
my_step.entrypoint()

# Define a Pipeline
@pipeline
def my_pipeline(my_step):
    my_step()

step_instance = my_step(params=MyStepParameters(param_1=17))
pipeline_instance = my_pipeline(my_step=step_instance)

# Configure and run the Pipeline
pipeline_instance.configure(enable_cache=False)
schedule = Schedule(...)
pipeline_instance.run(schedule=schedule)

# Fetch the Pipeline Run
last_run = pipeline_instance.get_runs()[0]
int_output = last_run.get_step["my_step"].outputs["int_output"].read()
```
{% endtab %}

{% tab title="New Syntax" %}
```python
from typing import Annotated, Optional, Tuple

from zenml import get_step_context, pipeline, step
from zenml.client import Client

# Define a Step
@step
def my_step(
    param_1: int, param_2: Optional[float] = None
) -> Tuple[Annotated[int, "int_output"], Annotated[str, "str_output"]]:
    result = int(param_1 * (param_2 or 1))
    result_uri = get_step_context().get_output_artifact_uri()
    return result, result_uri

# Run the Step separately
my_step()

# Define a Pipeline
@pipeline
def my_pipeline():
    my_step(param_1=17)

# Configure and run the Pipeline
my_pipeline = my_pipeline.with_options(enable_cache=False, schedule=schedule)
my_pipeline()

# Fetch the Pipeline Run
last_run = my_pipeline.last_run
int_output = last_run.steps["my_step"].outputs["int_output"].load()
```
{% endtab %}
{% endtabs %}

## Defining steps

{% tabs %}
{% tab title="Old Syntax" %}
```python
from zenml.steps import step, BaseParameters
from zenml.pipelines import pipeline

# Old: Subclass `BaseParameters` to define parameters for a step
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
```
{% endtab %}

{% tab title="New Syntax" %}
```python
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
{% endtab %}
{% endtabs %}

Check out [this page](../../how-to/build-pipelines/use-pipeline-step-parameters.md) for more information on how to parameterize your steps.

## Calling a step outside of a pipeline

{% tabs %}
{% tab title="Old Syntax" %}
```python
from zenml.steps import step

@step
def my_step() -> None:
    ...

my_step.entrypoint()  # Old: Call `step.entrypoint(...)`
```
{% endtab %}

{% tab title="New Syntax" %}
```python
from zenml import step

@step
def my_step() -> None:
    ...

my_step()  # New: Call the step directly `step(...)`
```
{% endtab %}
{% endtabs %}

## Defining pipelines

{% tabs %}
{% tab title="Old Syntax" %}
```python
from zenml.pipelines import pipeline

@pipeline
def my_pipeline(my_step):  # Old: steps are arguments of the pipeline function
    my_step()
```
{% endtab %}

{% tab title="New Syntax" %}
```python
from zenml import pipeline, step

@step
def my_step() -> None:
    ...

@pipeline
def my_pipeline():
    my_step()  # New: The pipeline function calls the step directly
```
{% endtab %}
{% endtabs %}

## Configuring pipelines

{% tabs %}
{% tab title="Old Syntax" %}
```python
from zenml.pipelines import pipeline
from zenml.steps import step

@step
def my_step() -> None:
    ...

@pipeline
def my_pipeline(my_step):
    my_step()

# Old: Create an instance of the pipeline and then call `pipeline_instance.configure(...)`
pipeline_instance = my_pipeline(my_step=my_step())
pipeline_instance.configure(enable_cache=False)
```
{% endtab %}

{% tab title="New Syntax" %}
```python
from zenml import pipeline, step

@step
def my_step() -> None:
    ...

@pipeline
def my_pipeline():
    my_step()

# New: Call the `with_options(...)` method on the pipeline
my_pipeline = my_pipeline.with_options(enable_cache=False)
```
{% endtab %}
{% endtabs %}

## Running pipelines

{% tabs %}
{% tab title="Old Syntax" %}
```python
from zenml.pipelines import pipeline
from zenml.steps import step

@step
def my_step() -> None:
    ...

@pipeline
def my_pipeline(my_step):
    my_step()

# Old: Create an instance of the pipeline and then call `pipeline_instance.run(...)`
pipeline_instance = my_pipeline(my_step=my_step())
pipeline_instance.run(...)
```
{% endtab %}

{% tab title="New Syntax" %}
```python
from zenml import pipeline, step

@step
def my_step() -> None:
    ...

@pipeline
def my_pipeline():
    my_step()

my_pipeline()  # New: Call the pipeline
```
{% endtab %}
{% endtabs %}

## Scheduling pipelines

{% tabs %}
{% tab title="Old Syntax" %}
```python
from zenml.pipelines import pipeline, Schedule
from zenml.steps import step

@step
def my_step() -> None:
    ...

@pipeline
def my_pipeline(my_step):
    my_step()

# Old: Create an instance of the pipeline and then call `pipeline_instance.run(schedule=...)`
schedule = Schedule(...)
pipeline_instance = my_pipeline(my_step=my_step())
pipeline_instance.run(schedule=schedule)
```
{% endtab %}

{% tab title="New Syntax" %}
```python
from zenml.pipelines import Schedule
from zenml import pipeline, step

@step
def my_step() -> None:
    ...

@pipeline
def my_pipeline():
    my_step()

# New: Set the schedule using the `pipeline.with_options(...)` method and then run it
schedule = Schedule(...)
my_pipeline = my_pipeline.with_options(schedule=schedule)
my_pipeline()
```
{% endtab %}
{% endtabs %}

Check out [this page](../../how-to/build-pipelines/schedule-a-pipeline.md) for more information on how to schedule your pipelines.

## Fetching pipelines after execution

{% tabs %}
{% tab title="Old Syntax" %}
```python
pipeline: PipelineView = zenml.post_execution.get_pipeline("first_pipeline")

last_run: PipelineRunView = pipeline.runs[0]
# OR: last_run = my_pipeline.get_runs()[0]

model_trainer_step: StepView = last_run.get_step("model_trainer")

model: ArtifactView = model_trainer_step.output
loaded_model = model.read()
```
{% endtab %}

{% tab title="New Syntax" %}
```python
pipeline: PipelineResponseModel = zenml.client.Client().get_pipeline("first_pipeline")
# OR: pipeline = pipeline_instance.model

last_run: PipelineRunResponseModel = pipeline.last_run  
# OR: last_run = pipeline.runs[0] 
# OR: last_run = pipeline.get_runs(custom_filters)[0] 
# OR: last_run = pipeline.last_successful_run

model_trainer_step: StepRunResponseModel = last_run.steps["model_trainer"]

model: ArtifactResponseModel = model_trainer_step.output
loaded_model = model.load()
```
{% endtab %}
{% endtabs %}

Check out [this page](../../how-to/track-metrics-metadata/fetch-metadata-within-steps.md) for more information on how to programmatically fetch information about previous pipeline runs.

## Controlling the step execution order

{% tabs %}
{% tab title="Old Syntax" %}
```python
from zenml.pipelines import pipeline

@pipeline
def my_pipeline(step_1, step_2, step_3):
    step_1()
    step_2()
    step_3()
    step_3.after(step_1)  # Old: Use the `step.after(...)` method
    step_3.after(step_2)
```
{% endtab %}

{% tab title="New Syntax" %}
```python
from zenml import pipeline

@pipeline
def my_pipeline():
    step_1()
    step_2()
    step_3(after=["step_1", "step_2"])  # New: Pass the `after` argument when calling a step
```
{% endtab %}
{% endtabs %}

Check out [this page](../../how-to/build-pipelines/control-execution-order-of-steps.md) for more information on how to control the step execution order.

## Defining steps with multiple outputs

{% tabs %}
{% tab title="Old Syntax" %}
```python
# Old: Use the `Output` class
from zenml.steps import step, Output

@step
def my_step() -> Output(int_output=int, str_output=str):
    ...
```
{% endtab %}

{% tab title="New Syntax" %}
```python
# New: Use a `Tuple` annotation and optionally assign custom output names
from typing_extensions import Annotated
from typing import Tuple
from zenml import step

# Default output names `output_0`, `output_1`
@step
def my_step() -> Tuple[int, str]:
    ...

# Custom output names
@step
def my_step() -> Tuple[
    Annotated[int, "int_output"],
    Annotated[str, "str_output"],
]:
    ...
```
{% endtab %}
{% endtabs %}

Check out [this page](../../how-to/build-pipelines/step-output-typing-and-annotation.md) for more information on how to annotate your step outputs.

## Accessing run information inside steps

{% tabs %}
{% tab title="Old Syntax" %}
```python
from zenml.steps import StepContext, step
from zenml.environment import Environment

@step
def my_step(context: StepContext) -> Any:  # Old: `StepContext` class defined as arg
    env = Environment().step_environment
    output_uri = context.get_output_artifact_uri()
    step_name = env.step_name  # Old: Run info accessible via `StepEnvironment`
    ...
```
{% endtab %}

{% tab title="New Syntax" %}
```python
from zenml import get_step_context, step

@step
def my_step() -> Any:  # New: StepContext is no longer an argument of the step
    context = get_step_context()
    output_uri = context.get_output_artifact_uri()
    step_name = context.step_name  # New: StepContext now has ALL run/step info
    ...
```
{% endtab %}
{% endtabs %}

Check out [this page](../../how-to/track-metrics-metadata/fetch-metadata-within-steps.md) for more information on how to fetch run information inside your steps using `get_step_context()`.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
