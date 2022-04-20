---
description: Familiarize yourself with the ZenML Basics
---

# Build a Pipeline
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

# Inspect Past runs

## Post-execution workflow

After executing a pipeline, the user needs to be able to fetch it from history and perform certain tasks. This page 
captures these workflows at an orbital level.

## Component Hierarchy

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

```python
# get all pipelines from all stacks
pipelines = repo.get_pipelines()  

# or get one pipeline by name and/or stack key
pipeline = repo.get_pipeline(pipeline_name=..., stack_key=...)
```

#### Runs

```python
runs = pipeline.runs  # all runs of a pipeline chronlogically ordered
run = runs[-1]  # latest run

# or get it by name
run = pipeline.get_run(run_name="custom_pipeline_run_name")
```

#### Steps

```python
# at this point we switch from the `get_` paradigm to properties
steps = run.steps  # all steps of a pipeline
step = steps[0]
print(step.entrypoint_name)
```

#### Outputs

```python
# The outputs of a step
# if multiple outputs they are accessible by name
output = step.outputs["output_name"]

# if one output, use the `.output` property instead 
output = step.output 

# will get you the value from the original materializer used in the pipeline
output.read()  
```

### Materializing outputs (or inputs)

Once an output artifact is acquired from history, one can visualize it with any chosen `Visualizer`.

```python
from zenml.materializers import PandasMaterializer


df = output.read(materializer_class=PandasMaterializer)
df.head()
```

### Retrieving Model

```python
from zenml.integrations.tensorflow.materializers.keras_materializer import KerasMaterializer    


model = output.read(materializer_class=KerasMaterializer)
model  # read keras.Model
```

## Visuals

### Seeing statistics

```python
from zenml.integrations.facets.visualizers.facet_statistics_visualizer import (
    FacetStatisticsVisualizer,
)

FacetStatisticsVisualizer().visualize(output)
```

It produces the following visualization:

![Statistics for boston housing dataset](../../assets/statistics-boston-housing.png)

