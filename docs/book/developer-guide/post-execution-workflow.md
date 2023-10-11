---
description: Inspect a Finished Pipeline Run.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To check the latest version please [visit https://docs.zenml.io](https://docs.zenml.io)
{% endhint %}


# Post Execution Workflow

After executing a pipeline, the user needs to be able to fetch it from history and perform certain tasks. This page 
captures these workflows at an orbital level.

## Accessing past pipeline runs

In the context of a post-execution workflow, there is an implied hierarchy of some basic ZenML components:

```shell
repository -> pipelines -> runs -> steps -> outputs

# where -> implies a 1-many relationship.
```

### Repository

The highest level `Repository` object is where to start from.

```python
from zenml.repository import Repository

repo = Repository()
```

### Pipelines

The repository contains a collection of all created pipelines with at least one run sorted by the time of their first 
run from oldest to newest.

```python
# get all pipelines from all stacks
pipelines = repo.get_pipelines()  

# now you can get pipelines by index
pipeline_x = pipelines[-1]

# or get one pipeline by name and/or stack key
pipeline_x = repo.get_pipeline(pipeline_name=..., stack_key=...)
```

The pipeline name is the name of the decorated function (or the Pipeline class in case of the 
[Class Based API](class-based-api.md)).

```python
from zenml.pipelines import pipeline

@pipeline()
def this_is_the_pipeline_name():
    ...
```

{% hint style="info" %}
Be careful when accessing pipelines by index. Even if you just ran a pipeline it might not be at index `-1`, due to the 
fact that the pipelines are sorted by time of `first` run. As such it is recommended to access the pipeline by its name
{% endhint %}

### Runs

Each pipeline can be executed many times. You can easily get a list of all runs like this

```python
runs = pipeline_x.runs  # all runs of a pipeline chronologically ordered

# get the last run by index, runs are ordered by execution time in ascending order
run = runs[-1]

# or get a specific run by name
run = pipeline_x.get_run(run_name=...)
```

### Steps

Within a given pipeline run you can now zoom in further on the individual steps.

```python
steps = run.steps  # all steps of a pipeline
step = steps[0]
print(step.entrypoint_name)
```

The steps are ordered by time of execution. Depending on the 
[orchestrator](../core-concepts.md#orchestrator), steps can be run in parallel. As such, accessing steps by 
index can be unreliable across different runs. Instead, it makes sense to access steps by their name.

```python
run.get_step(name=...)
```

The step name is the name of the decorated function (or the `Step` class in case of the 
[class-based API](class-based-api.md)).

```python
from zenml.steps import step

@step
def this_is_the_step_name():
    ...
```

### Outputs

Most of your steps will probably create outputs. You'll be able to inspect these outputs like this:

```python
# The outputs of a step
# if there are multiple outputs they are accessible by name
output = step.outputs["output_name"]

# if one output, use the `.output` property instead 
output = step.output 

# will read the value into memory
output.read()  
```

The names of the outputs can be found in the `Output` typing for your steps:

```python
from zenml.steps import step, Output

@step
def some_step() -> Output(output_name=int):
    ...
```
