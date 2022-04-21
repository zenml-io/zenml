---
description: Familiarize yourself with the ZenML Basics
---

# Getting started with a Pipeline

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

# Interact with completed runs

After executing a pipeline, the user needs to be able to fetch it from history and perform certain tasks. This page 
captures these workflows at an orbital level.

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

# How data flows through steps

As described above a ZenML pipeline is built in a data centric way. The outputs and inputs
of steps define how steps are connected and the order in which they are executed. Each step should be considered as 
its very own process that reads and writes its inputs and outputs from and to the artifact store. This is where 
**materializers** come into play.


## What is a materializer?

A materializer dictates how a given artifact can be written to and retrieved from the artifact store. It contains
all serialization and deserialization logic. 

```python
class BaseMaterializer(metaclass=BaseMaterializerMeta):
    """Base Materializer to realize artifact data."""

    ASSOCIATED_ARTIFACT_TYPES = ()
    ASSOCIATED_TYPES = ()

    def __init__(self, artifact: "BaseArtifact"):
        """Initializes a materializer with the given artifact."""
        self.artifact = artifact

    def handle_input(self, data_type: Type[Any]) -> Any:
        """Write logic here to handle input of the step function.

        Args:
            data_type: What type the input should be materialized as.
        Returns:
            Any object that is to be passed into the relevant artifact in the
            step.
        """
        # read from self.artifact.uri
        ...

    def handle_return(self, data: Any) -> None:
        """Write logic here to handle return of the step function.

        Args:
            data: Any object that is specified as an input artifact of the step.
        """
        # write `data` to self.artifact.uri
        ...
```

Above you can see the basic definition of the `BaseMaterializer`. All other materializers inherit from this class, and 
this class defines the interface of all materializers. 

Each materializer has an `artifact` object. The most important property of an `artifact` object is the `uri`. The 
`uri` is created by ZenML at pipeline run time and points to the directory of a file system (the artifact store).

The `handle_input` and `handle_return` functions are important. 

- `handle_input` is responsible for **reading** the artifact from the artifact store.
- `handle_return` is responsible for **writing** the artifact to the artifact store.

Each materializer has `ASSOCIATED_TYPES` and `ASSOCIATED_ARTIFACT_TYPES`.

- `ASSOCIATED_TYPES` is the data type that is being stored. ZenML uses this information to call the right materializer 
at the right time. i.e. If a ZenML step returns a `pd.DataFrame`, ZenML will try to find any materializer that has 
`pd.DataFrame` (or its subclasses) in its `ASSOCIATED_TYPES`.
- `ASSOCIATED_ARTIFACT_TYPES` simply define what `type` of artifacts are being stored. This can be `DataArtifact`, 
`StatisticsArtifact`, `DriftArtifact`, etc. This is simply a tag to query certain artifact types in the post-execution 
workflow.

## Extending the `BaseMaterializer`

In order to control more precisely how data flowing between steps is treated, one can simply extend the 
`BaseMaterializer` by sub-classing it.

```python
class MyCustomMaterializer(BaseMaterializer):
    """Define my own materialization logic"""
    ASSOCIATED_ARTIFACT_TYPES = (...)
    ASSOCIATED_TYPES = (...)


    def handle_input(self, data_type: Type[Any]) -> Any:
        # read from self.artifact.uri
        ...

    def handle_return(self, data: Any) -> None:
        # write `data` to self.artifact.uri
        ...
```

For example, let's say you a custom object called `MyObject` that flows between two steps in a pipeline:

```python
from zenml.steps import step
from zenml.pipelines import pipeline


class MyObj:
    def __init__(self, name: str):
        self.name = name

@step
def step1() -> MyObj:
    return MyObj("jk")

@step
def step1(my_obj: MyObj):
    print(my_obj)

@pipeline
def pipe(step1, step2):
    step2(step1())

pipe(
    step1=step1(), 
    step2=step2()
).run()
```

Running the above without a custom materializer will result in the following error:

```shell
zenml.exceptions.StepInterfaceError: Unable to find materializer for output 'output' of 
type `<class '__main__.MyObj'>` in step 'step1'. Please make sure to either explicitly set a materializer for step 
outputs using `step.with_return_materializers(...)` or registering a default materializer for specific types by 
subclassing `BaseMaterializer` and setting its `ASSOCIATED_TYPES` class variable. 
For more information, visit https://docs.zenml.io/guides/common-usecases/custom-materializer.
```

The above basically means that ZenML does not know how to persist the object of type `MyObj` between steps (how could 
it? We just created this!). Therefore, we can create our own materializer:

```python
import os
from typing import Type

from zenml.artifacts import DataArtifact
from zenml.io import fileio
from zenml.materializers.base_materializer import BaseMaterializer

class MyMaterializer(BaseMaterializer):
    ASSOCIATED_TYPES = (MyObj, )
    ASSOCIATED_ARTIFACT_TYPES = (DataArtifact, )

    def handle_input(self, data_type: Type[MyObj]) -> MyObj:
        """Read from artifact store"""
        super().handle_input(data_type)
        with fileio.open(os.path.join(self.artifact.uri, 'data.txt'), 'r') as f:
            name = f.read()
        return MyObj(name=name)

    def handle_return(self, my_obj: MyObj) -> None:
        """Write to artifact store"""
        super().handle_return(my_obj)
        with fileio.open(os.path.join(self.artifact.uri, 'data.txt'), 'w') as f:
            f.write(my_obj.name)
```

Pro-tip: Use the ZenML `fileio` handler to ensure your materialization logic works across artifact stores (local and 
remote like S3 buckets).

Then edit the pipeline as follows:

```python
pipe(
    step1=step1().with_return_materializers(MyMaterializer),
    step2=step2()
).run()
```

Please note that for multiple outputs a dictionary can be supplied of type `{OUTPUT_NAME: MATERIALIZER_CLASS}` to the 
`with_return_materializers` function.

Also, notice that `with_return_materializers` need only be called on `step1`, all downstream steps will use the same 
materializer by default.

This will yield the proper response as follows:

```shell
Creating run for pipeline: `pipe`
Cache enabled for pipeline `pipe`
Using stack `local_stack` to run pipeline `pipe`...
Step `step1` has started.
Step `step1` has finished in 0.035s.
Step `step2` has started.
jk
Step `step2` has finished in 0.036s.
Pipeline run `pipe-24_Jan_22-23_12_18_504593` has finished in 0.080s.
```