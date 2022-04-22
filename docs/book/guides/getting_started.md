---
description: Familiarize yourself with the ZenML Basics
---

# Installation & Setup

## Welcome

Your first step is to install **ZenML**, which comes bundled as a good old `pip` package.

{% hint style="warning" %}
Please note that we only support Python >= 3.7 <3.9, so please adjust your python environment accordingly.
{% endhint %}

## Virtual Environment

We highly encourage you to install **ZenML** in a virtual environment. We like to use 
[virtualenvwrapper](https://virtualenvwrapper.readthedocs.io/en/latest/) to manage our Python virtual environments.

## Install with pip

When you're set with your environment, run:

```bash
pip install zenml
```

Alternatively, if you’re feeling brave, feel free to install the bleeding edge: **NOTE:** Do so at your own risk;
no guarantees given!

```bash
pip install git+https://github.com/zenml-io/zenml.git@main --upgrade
```

Once the installation is completed, you can check whether the installation was successful through:

### Bash

```bash
zenml version
```

### Python

```python
import zenml
print(zenml.__version__)
```

If you would like to learn more about the current release, please visit our[PyPi package page.](https://pypi.org/project/zenml)

## Running with Docker

`zenml` is available as a docker image hosted publicly on [DockerHub](https://hub.docker.com/r/zenmldocker/zenml). Use the following command to get started in a bash environment with `zenml` available:

```
docker run -it zenmldocker/zenml /bin/bash
```

## Enabling auto-completion on the CLI

{% tabs %}
{% tab title="Bash" %}
For Bash, add this to `~/.bashrc`:
```bash
eval "$(_ZENML_COMPLETE=source_bash zenml)"
```
{% endtab %}

{% tab title="Zsh" %}
For Zsh, add this to `~/.zshrc`:

```bash
eval "$(_ZENML_COMPLETE=source_zsh zenml)"
```
{% endtab %}

{% tab title="Fish" %}
For Fish, add this to `~/.config/fish/completions/foo-bar.fish`:

```bash
eval (env _ZENML_COMPLETE=source_fish zenml)
```
{% endtab %}
{% endtabs %}

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

# Visualizing Results

## What is a Visualizer?

Sometimes it makes sense in the [post-execution workflow](basics/post-execution-workflow.md) to actually visualize step outputs. 
ZenML has a standard, extensible interface for all visualizers:

```python
class BaseVisualizer:
    """Base class for all ZenML Visualizers."""

    @abstractmethod
    def visualize(self, object: Any, *args: Any, **kwargs: Any) -> None:
        """Method to visualize objects."""
```

The `object` can currently be a `StepView`, a `PipelineRunView` , or a `PipelineView`. (These are all different 
post-execution objects.)

## Examples of visualizations

### Lineage with [`dash`](https://plotly.com/dash/)

```python
from zenml.repository import Repository
from zenml.integrations.dash.visualizers.pipeline_run_lineage_visualizer import (
    PipelineRunLineageVisualizer,
)

repo = Repository()
latest_run = repo.get_pipelines()[-1].runs[-1]
PipelineRunLineageVisualizer().visualize(latest_run)
```

It produces the following visualization:

![Lineage Diagram](../assets/zenml-pipeline-run-lineage-dash.png)

### Statistics with [`facets`](https://github.com/PAIR-code/facets)

```python
from zenml.integrations.facets.visualizers.facet_statistics_visualizer import (
    FacetStatisticsVisualizer,
)

FacetStatisticsVisualizer().visualize(output)
```

It produces the following visualization:

![Statistics for boston housing dataset](../assets/statistics-boston-housing.png)

# How data flows through steps

As described above a ZenML pipeline is built in a data centric way. The outputs and inputs
of steps define how steps are connected and the order in which they are executed. Each step should be considered as 
its very own process that reads and writes its inputs and outputs from and to the artifact store. This is where 
**materializers** come into play.


## What is a materializer?

A materializer dictates how a given artifact can be written to and retrieved from the artifact store. It contains
all serialization and deserialization logic. 

```python
from typing import Type, Any
from zenml.materializers.base_materializer import BaseMaterializerMeta

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

Let's say you a custom object called `MyObject` that flows between two steps in a pipeline:

```python
from zenml.steps import step
from zenml.pipelines import pipeline


class MyObj:
    def __init__(self, name: str):
        self.name = name

@step
def my_first_step() -> MyObj:
    """Step that returns an object of type MyObj"""
    return MyObj("my_object")

@step
def my_second_step(my_obj: MyObj) -> None:
    """Step that prints the input object and returns nothing."""
    print(f"The following object was passed to this step: `{my_obj.name}`")

@pipeline
def first_pipeline(
    step_1,
    step_2
):
    output_1 = step_1()
    step_2(output_1)

first_pipeline(step_1=my_first_step(),step_2=my_second_step()).run()
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
it? We just created this!). Therefore, we can have to create our own materializer. TO do this you can simply extend the 
`BaseMaterializer` by sub-classing it.


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

Now ZenML can use this materializer to handle outputs and inputs of your customs object. Edit the pipeline as follows, 
to see this in action:

```python
first_pipeline(
    step_1=my_first_step().with_return_materializers(MyMaterializer),
    step_2=my_second_step()).run()
```

Please note that for multiple outputs a dictionary can be supplied of type `{OUTPUT_NAME: MATERIALIZER_CLASS}` to the 
`with_return_materializers` function.

Also, notice that `with_return_materializers` need only be called on `step1`, all downstream steps will use the same 
materializer by default.

This will yield the proper response as follows:

```shell
Creating run for pipeline: `first_pipeline`
Cache enabled for pipeline `first_pipeline`
Using stack `default` to run pipeline `first_pipeline`...
Step `my_first_step` has started.
Step `my_first_step` has finished in 0.081s.
Step `my_second_step` has started.
The following object was passed to this step: `my_object`
Step `my_second_step` has finished in 0.048s.
Pipeline run `first_pipeline-22_Apr_22-10_58_51_135729` has finished in 0.153s.
```

# Caching and ZenML

Machine learning pipelines are rerun many times over throughout their development lifecycle. Prototyping is often a 
fast and iterative process that benefits a lot from caching. This makes caching a very powerful tool. (Read 
[our blogpost](https://blog.zenml.io/caching-ml-pipelines/) for more context on the benefits of caching.)

## 📈 Benefits of Caching
- **🔁 Iteration Efficiency** - When experimenting, it really pays to have a high frequency of iteration. You learn 
when and how to course correct earlier and more often. Caching brings you closer to that by making the costs of 
frequent iteration much lower.
- **💪 Increased Productivity** - The speed-up in iteration frequency will help you solve problems faster, making 
stakeholders happier and giving you a greater feeling of agency in your machine learning work.
- **🌳 Environmental Friendliness** - Caching saves you the 
[needless repeated computation steps](https://machinelearning.piyasaa.com/greening-ai-rebooting-the-environmental-harms-of-machine/) 
which mean you use up and waste less energy. It all adds up!
- **＄ Reduced Costs** - Your bottom-line will thank you! Not only do you save the planet, but your monthly cloud 
bills might be lower on account of your skipping those repeated steps.

## Caching in ZenML

ZenML comes with caching enabled by default. As long as there is no change within a step or upstream from it, the 
cached outputs of that step will be used for the next pipeline run. This means that whenever there are code or 
configuration changes affecting a step, the step will be rerun in the next pipeline execution. Currently, the 
caching does not automatically detect changes within the file system or on external APIs. Make sure to set caching 
to `False` on steps that depend on external input or if the step should run regardless of caching.

There are multiple ways to take control of when and where caching is used.

### Caching on a Pipeline Level

On a pipeline level the caching policy can easily be set as a parameter within the decorator. If caching is explicitly 
turned off on a pipeline level, all steps are run without caching, even if caching is set to true for single 
steps.

```python
@pipeline(enable_cache=False)
def first_pipeline(....):
    """Pipeline with cache disabled"""
```

### Control Caching on a Step Level

Caching can also be explicitly turned off at a step level. You might want to turn off caching for steps that take 
external input (like fetching data from an API/ File IO).

```python
@step(enable_cache=False)
def import_data_from_api(...):
    """Import most up-to-date data from public api"""
    ...
    
@pipeline(enable_cache=True)
def pipeline(....):
    """Pipeline with cache disabled"""
```

### Control Caching within the Runtime Configuration

Sometimes you want to have control over caching at runtime instead of defaulting to the backed in configurations of 
your pipeline and its steps. ZenML offers a way to override all caching settings of the pipeline at runtime.

```python
first_pipeline(step_1=..., step_2=...).run(enable_cache=False)
```

### Invalidation of Cache

Caching is invalidated whenever any changes in step **code** or step **configuration** is detected. ZenML can **not** 
detect changes in upstream APIs or in the Filesystem. Make sure you disable caching for steps that rely on these sources 
if your pipeline needs to have access to the most up-to date data. During development, you probably don't care as much 
about the freshness of your data. In that case feel free to keep caching enabled and enjoy the faster runtimes.

