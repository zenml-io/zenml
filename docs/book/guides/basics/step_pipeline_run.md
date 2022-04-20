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
    return 2 * input_int, 2* input_float
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
        return 2 * input_int, 2* input_float


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
