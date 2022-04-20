---
description: Familiarize yourself with the ZenML Basics
---

# Build a Pipeline

{% tabs %}
{% tab title="Guide" %}
## Create steps

Steps are the atomic components of a ZenML pipeline. Each step is defined by its inputs, the logic it applies and its 
outputs. Here is a very simple example of such a step:

```python
from zenml.steps import step, Output

@step
def my_first_step() -> Output(output_int=int, output_float=float):
    """Step that returns a pre-defined integer and float"""
    return 7, 0.1
```

As this step has multiple outputs, we need to use the `zenml.steps.step_output.Output` class to indicate the names 
of each output. These names can be used to directly access an output within the [post execution workflow].

Let's come up with a second step that consumes the output of our first step and performs some sort of transformation
on it. In this case, let's double the input.

```python
from zenml.steps import step, Output

@step
def my_second_step(input_int: int, input_float: float) -> Output(output_int=int, output_float=float):
    """Step that doubles the inputs"""
    return 2 * input_int, 2 * input_float
```

Now we can go ahead and create a pipeline with our two steps to make sure they work.

## Define the Pipeline

Here we define the pipeline. This is done implementation agnostic by simply routing outputs through the 
steps within the pipeline. You can think of this as a recipe for how we want data to flow through our steps.


```python
@pipeline
def first_pipeline(
    step_1,
    step_2
):
    output_1, output_2 = step_1()
    step_2(output_1, output_2)
```

## Instantiate and run your Pipeline

With your pipeline recipe in hand you can now specify which particular steps implement the pipeline. And with that, you
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
{% endtab %}

{% tab title="Code" %}
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
{% endtab %}
{% endtabs %}

# Configure at Runtime

A ZenML pipeline clearly separated business logic from parameter configuration. Business logic is what defines 
a step and the pipeline. Step and pipeline configurations are used to dynamically set parameters at runtime. 

{% tabs %}
{% tab title="Guide" %}
## Step configuration

You can easily add a configuration to a step by creating your configuration as a subclass to the BaseStepConfig. 
When such a config object is passed to a step, it is not treated like other artifacts. Instead, it gets passed
into the step when the pipeline is instantiated.

```python
from zenml.steps import step, Output, BaseStepConfig

class SecondStepConfig(BaseStepConfig):
    """Trainer params"""
    multiplier: int = 4


@step
def my_second_step(config: SecondStepConfig, input_int: int, input_float: float
                   ) -> Output(output_int=int, output_float=float):
    """Step that multiplie the inputs"""
    return config.multiplier * input_int, config.multiplier * input_float
```

The default value for the multiplier is set to 4. However, when the pipeline is instatiated you can
override the default like this:

```python
first_pipeline(step_1=my_first_step(),
               step_2=my_second_step(SecondStepConfig(multiplier=3))
               ).run()
```

## Naming a pipeline run

When running a pipeline by calling `my_pipeline.run()`, ZenML uses the current date and time as the name for the 
pipeline run. In order to change the name for a run, simply pass it as a parameter to the `run()` function:

```python
first_pipeline_instance.run(run_name="custom_pipeline_run_name")
```

{% hint style="warning" %}
Pipeline run names must be unique, so make sure to compute it dynamically if you plan to run your pipeline multiple 
times.
{% endhint %}

Once the pipeline run is finished we can easily access this specific run during our post-execution workflow:

```python
from zenml.repository import Repository

repo = Repository()
pipeline = repo.get_pipeline(pipeline_name="first_pipeline")
run = pipeline.get_run("custom_pipeline_run_name")
```

## Setting step parameters using a config file

In addition to setting parameters for your pipeline steps in code as seen above, ZenML also allows you to use a 
configuration [yaml](https://yaml.org) file. This configuration file must follow the following structure:

```yaml
steps:
  step_name:
    parameters:
      parameter_name: parameter_value
      some_other_parameter_name: 2
  some_other_step_name:
    ...
```

For our example from above this results in the following configuration yaml.&#x20;

```yaml
steps:
  step_2:
    parameters:
      multiplier: 3
```

Use the configuration file by calling the pipeline method `with_config(...)`:

```python
first_pipeline(step_1=my_first_step(),
               step_2=my_second_step()
               ).with_config("path_to_config.yaml").run()
```
{% endtab %}

{% tab title="Code" %}
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
def my_second_step(config: SecondStepConfig, input_int: int, input_float: float
                   ) -> Output(output_int=int, output_float=float):
    """Step that multiplie the inputs"""
    return config.multiplier * input_int, config.multiplier * input_float

@pipeline
def first_pipeline(
    step_1,
    step_2
):
    output_1, output_2 = step_1()
    step_2(output_1, output_2)
    
first_pipeline(step_1=my_first_step(),
               step_2=my_second_step(SecondStepConfig(multiplier=3))
               ).run(run_name="custom_pipeline_run_name")
```
{% endtab %}
{% endtabs %}

# Interact with completed runs

After executing a pipeline, the user needs to be able to fetch it from history and perform certain tasks. This page 
captures these workflows at an orbital level.

{% tabs %}
{% tab title="Guide" %}
## Accessing past pipeline runs

In the context of a post-execution workflow, there is an implied hierarchy of some basic ZenML components:

```shell
repository -> pipelines -> runs -> steps -> outputs

# where -> implies a 1-many relationship.
```

### Repository

The highest level `repository` object is where to start from.

```python
from zenml.repository import Repository

repo = Repository()
```

#### Pipelines

The repository contains a collection of all created pipelines with at least one run.

```python
# get all pipelines from all stacks
pipelines = repo.get_pipelines()  

# now you can get pipelines by index
pipeline_x = pipelines[-1]

# or get one pipeline by name and/or stack key
pipeline_x = repo.get_pipeline(pipeline_name=..., stack_key=...)
```

#### Runs

Each pipeline can be executed many times. You can easily get a list of all runs like this

```python
runs = pipeline_x.runs  # all runs of a pipeline chronlogically ordered

# get the last run by index
run = runs[-1]

# or get a specific run by name
run = pipeline_x.get_run(run_name=...)
```

#### Steps

Within a given pipeline run you can now zoom in further on the individual steps.

```python
steps = run.steps  # all steps of a pipeline
step = steps[0]
print(step.entrypoint_name)
```

#### Outputs

Most of your steps will probably create outputs. You'll be able to inspect these outputs like this:

```python
# The outputs of a step
# if there are multiple outputs they are accessible by name
output = step.outputs["output_name"]

# if one output, use the `.output` property instead 
output = step.output 

# will get you the value from the original materializer used in the pipeline
output.read()  
```
{% endtab %}

{% tab title="Code" %}
```python
from zenml.repository import Repository

repo = Repository()
pipelines = repo.get_pipelines()  

# now you can get pipelines by index
pipeline_x = pipelines[-1]

# all runs of a pipeline chronlogically ordered
runs = pipeline_x.runs  

# get the last run by index
run = runs[-1]

# all steps of a pipeline
steps = run.steps  
step = steps[0]
print(step.entrypoint_name)

# The outputs of a step, if there are multiple outputs they are accessible by name
output = step.outputs["output_int"]

# will get you the value from the original materializer used in the pipeline
output.read()  
```
{% endtab %}
{% endtabs %}


# Using Visualizers