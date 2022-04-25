---
description: Familiarize yourself with the ZenML Basics
---

# Installation
### Welcome

Your first step is to install **ZenML**, which comes bundled as a good old `pip` package.

{% hint style="warning" %}
Please note that we only support Python >= 3.7 <3.9, so please adjust your python environment accordingly.
{% endhint %}

### Virtual Environment

We highly encourage you to install **ZenML** in a virtual environment. We like to use 
[virtualenvwrapper](https://virtualenvwrapper.readthedocs.io/en/latest/) to manage our Python virtual environments.

### Install with pip

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

If you would like to learn more about the current release, please visit our 
[PyPi package page.](https://pypi.org/project/zenml)

### Running with Docker

`zenml` is available as a docker image hosted publicly on [DockerHub](https://hub.docker.com/r/zenmldocker/zenml). Use the following command to get started in a bash environment with `zenml` available:

```
docker run -it zenmldocker/zenml /bin/bash
```

### Enabling auto-completion on the CLI

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

# Steps & Pipelines

## Step

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

## Pipeline

Here we define the pipeline. This is done implementation agnostic by simply routing outputs through the 
steps within the pipeline. You can think of this as a recipe for how we want data to flow through our steps.


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
<details>
    <summary>Minimal Code Example</summary>

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

# Runtime Configuration

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

This functionality is based on [Step Fixtures](#step-fixtures) which you will learn more about below.

### Setting step parameters using a config file

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

## Pipeline Run Name

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

<details>
    <summary>Minimal Code Example</summary>

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

# Post Execution Workflow

After executing a pipeline, the user needs to be able to fetch it from history and perform certain tasks. This page 
captures these workflows at an orbital level.

### Accessing past pipeline runs

In the context of a post-execution workflow, there is an implied hierarchy of some basic ZenML components:

```shell
repository -> pipelines -> runs -> steps -> outputs

# where -> implies a 1-many relationship.
```

#### Repository

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

# Visualizers
### What is a Visualizer?

Sometimes it makes sense in the [post-execution workflow](basics/post-execution-workflow.md) to actually visualize step outputs. 
ZenML has a standard, extensible interface for all visualizers:

```python
from abc import abstractmethod
from typing import Any

class BaseVisualizer:
    """Base class for all ZenML Visualizers."""

    @abstractmethod
    def visualize(self, object: Any, *args: Any, **kwargs: Any) -> None:
        """Method to visualize objects."""
```

The `object` can currently be a `StepView`, a `PipelineRunView` , or a `PipelineView`. (These are all different 
post-execution objects.)

### Examples of visualizations

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

# Materializers

As described above a ZenML pipeline is built in a data centric way. The outputs and inputs
of steps define how steps are connected and the order in which they are executed. Each step should be considered as 
its very own process that reads and writes its inputs and outputs from and to the artifact store. This is where 
**materializers** come into play.

### What is a materializer?

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

### Extending the `BaseMaterializer`

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
<details>
    <summary>Minimal Code Example</summary>

```python
import os
from typing import Type

from zenml.steps import step
from zenml.pipelines import pipeline

from zenml.artifacts import DataArtifact
from zenml.io import fileio
from zenml.materializers.base_materializer import BaseMaterializer

class MyObj:
    def __init__(self, name: str):
        self.name = name

class MyMaterializer(BaseMaterializer):
    ASSOCIATED_TYPES = (MyObj,)
    ASSOCIATED_ARTIFACT_TYPES = (DataArtifact,)

    def handle_input(self, data_type: Type[MyObj]) -> MyObj:
        """Read from artifact store"""
        super().handle_input(data_type)
        with fileio.open(os.path.join(self.artifact.uri, 'data.txt'),
                         'r') as f:
            name = f.read()
        return MyObj(name=name)

    def handle_return(self, my_obj: MyObj) -> None:
        """Write to artifact store"""
        super().handle_return(my_obj)
        with fileio.open(os.path.join(self.artifact.uri, 'data.txt'),
                         'w') as f:
            f.write(my_obj.name)

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

first_pipeline(
    step_1=my_first_step().with_return_materializers(MyMaterializer),
    step_2=my_second_step()).run()
```
</details>

# Caching

Machine learning pipelines are rerun many times over throughout their development lifecycle. Prototyping is often a 
fast and iterative process that benefits a lot from caching. This makes caching a very powerful tool. (Read 
[our blogpost](https://blog.zenml.io/caching-ml-pipelines/) for more context on the benefits of caching.)

### Caching in ZenML

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

<details>
    <summary>Minimal Code Example</summary>

```python
from zenml.steps import step, Output, BaseStepConfig
from zenml.pipelines import pipeline

@step
def my_first_step() -> Output(output_int=int, output_float=float):
    """Step that returns a pre-defined integer and float"""
    return 7, 0.1

@step(enable_cache=False)
def my_second_step(input_int: int, input_float: float
                   ) -> Output(output_int=int, output_float=float):
    """Step that doubles the inputs"""
    return 2 * input_int, 2 * input_float

class SecondStepConfig(BaseStepConfig):
    """Trainer params"""
    multiplier: int = 4

@step
def my_configured_step(config: SecondStepConfig, input_int: int,
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

first_pipeline(step_1=my_first_step(),
               step_2=my_second_step()
               ).run()

# Step one will use cache, Step two will be rerun due to decorator config
first_pipeline(step_1=my_first_step(),
               step_2=my_second_step()
               ).run()

# Complete pipeline will be rerun
first_pipeline(step_1=my_first_step(),
               step_2=my_second_step()
               ).run(enable_cache=False)

first_pipeline(step_1=my_first_step(),
               step_2=my_configured_step(SecondStepConfig(multiplier=11))
               ).run()

# Step one will use cache, Step two is rerun as the config changed
first_pipeline(step_1=my_first_step(),
               step_2=my_configured_step(SecondStepConfig(multiplier=13))
               ).run()
```
</details>

# Step Fixtures

In general, when defining steps, you usually can only supply inputs that have been output by previous steps.
However, there are some special exceptions. 

* An object which is a subclass of `BaseStepConfig`: This object is used to pass run-time parameters to a pipeline run. 
It can be used to send parameters to a step that are not artifacts. You learned about this one already in the chapter
on [Step Configuration](#step-configuration)
* A `StepContext` object: This object gives access to the artifact store, metadata store, materializers, and special 
integration-specific libraries.

These special parameters are comparable to [pytest fixtures](https://docs.pytest.org/en/6.2.x/fixture.html), hence the 
name `Step Fixtures`.

`Step fixtures` are simple to use: Simply pass a parameter in with the right type hint as follows:

### Using fixtures in the Functional API

```python
@step
def my_step(
    config: SubClassBaseStepConfig,  # subclass of `BaseStepConfig`
    context: StepContext,
    artifact: str,  # all other parameters are artifacts, coming from upstream steps
):
    ...
```

Please note that the name of the parameter can be anything, but the type hint is what is important.

### Using the `BaseStepConfig`

`BaseStepConfig` instances can be passed when creating a step. 

We first need to sub-class it:

```python
from zenml.steps import BaseStepConfig

class MyConfig(BaseStepConfig):
    param_1: int = 1
    param_2: str = "one"
    param_3: bool = True
```

Behind the scenes, this class is essentially a [Pydantic BaseModel](https://pydantic-docs.helpmanual.io/usage/models/). 
Therefore, any type that [Pydantic supports](https://pydantic-docs.helpmanual.io/usage/types/) is supported. 

You can then pass it in a step as follows:

```python
from zenml.steps import step
@step
def my_step(
    config: MyConfig,
    ...
):
    config.param_1, config.param_2, config.param_3
```

If all properties in `MyConfig` have default values, then that is already enough. If they don't all have default values, 
then one must pass the config in during pipeline run time. You can also override default values here and therefore 
dynamically parameterize your pipeline runs.

```python
from zenml.pipelines import pipeline
@pipeline
def my_pipeline(my_step):
    ...

pipeline = my_pipeline(
    my_step=my_step(config=MyConfig(param_1=2)),
)
```

### Using the `StepContext`

Unlike `BaseStepConfig`, we can pass in the `StepContext` directly to a step without explicitely passing it at run-time.

The `StepContext` provides additional context inside a step function. It can be used to access artifacts directly from 
within the step.

You do not need to create a StepContext object yourself and pass it when creating the step, as long as you specify 
it in the signature ZenML will create the `StepContext` and automatically pass it when executing your step.

{% hint style="info" %}
When using a StepContext inside a step, ZenML disables caching for this step by default as the context provides 
access to external resources which might influence the result of your step execution. 
To enable caching anyway, explicitly enable it in the @step decorator or when initializing your custom step class.
{% endhint %}

Within a step, there are many things that you can use the `StepContext` object for. For example
materializers, artifact locations, etc ...

```python
from zenml.steps import StepContext, step

@step
def my_step(
    context: StepContext,
):
    context.get_output_materializer()  # Returns a materializer for a given step output.
    context.get_output_artifact_uri()  # Returns the URI for a given step output.
    context.metadata_store  # Access to the [Metadata Store](https://apidocs.zenml.io/latest/api_docs/metadata_stores/)
```

For more information, check the [API reference](https://apidocs.zenml.io/latest/api_docs/steps/)

The next [section](#fetching-historic-runs) will directly address one important use for the Step Context.

# Fetching historic runs
### The need to fetch historic runs

Sometimes, it is necessary to fetch information from previous runs in order to make a decision within a currently 
executing step. Examples of this:

* Fetch the best model evaluation results from all past pipeline runs to decide whether to deploy a newly-trained model.
* Fetching a model out of a list of trained models.
* Fetching the latest model produced by a different pipeline to run an inference on.

### Utilizing `StepContext`

ZenML allows users to fetch historical parameters and artifacts using the `StepContext` 
[fixture](step-fixtures.md).

As an example, see this step that uses the `StepContext` to query the metadata store while running a step.
We use this to evaluate all models of past training pipeline runs and store the current best model. 
In our inference pipeline, we could then easily query the metadata store to fetch the best performing model.

```python
from zenml.steps import step, StepContext

@step
def my_third_step(context: StepContext, input_int: int) -> bool:
    """Step that decides if this pipeline run produced the highest value
    for `input_int`"""
    highest_int = 0

    # Inspect all past runs of `first_pipeline`
    try:
        pipeline_runs = (context.metadata_store
                                .get_pipeline("first_pipeline")
                                .runs)
    except KeyError:
        # If this is the first time running this pipeline you don't want
        #  it to fail
        print('No previous runs found, this run produced the highest '
              'number by default.')
        return True
    else:
        for run in pipeline_runs:
            # get the output of the second step
            try:
                multiplied_output_int = (run.get_step("step_2")
                                            .outputs['multiplied_output_int']
                                            .read())
            except KeyError:
                # If you never ran the pipeline or ran it with steps that
                #  don't produce a step with the name
                #  `multiplied_output_int` then you don't want this to fail
                pass
            else:
                if multiplied_output_int > highest_int:
                    highest_int = multiplied_output_int

    if highest_int > input_int:
        print('Previous runs produced a higher number.')
        return False  # There was a past run that produced a higher number
    else:
        print('This run produced the highest number.')
        return True  # The current run produced the highest number
```

Just like that you are able to compare runs with each other from within the run itself. 

<details>
    <summary>Minimal Code Example</summary>

```python
from random import randint
from zenml.steps import step, Output, StepContext
from zenml.pipelines import pipeline

@step
def my_first_step() -> Output(output_int=int, output_float=float):
    """Step that returns a pre-defined integer and float"""
    return 7, 0.1

@step(enable_cache=False)
def my_second_step(
        input_int: int, input_float: float
) -> Output(multiplied_output_int=int, multiplied_output_float=float):
    """Step that doubles the inputs"""
    multiplier = randint(0, 100)
    return multiplier * input_int, multiplier * input_float

@step
def my_third_step(context: StepContext, input_int: int) -> bool:
    """Step that decides if this pipeline run produced the highest value
    for `input_int`"""
    highest_int = 0

    # Inspect all past runs of `first_pipeline`
    try:
        pipeline_runs = (context.metadata_store
                                .get_pipeline("first_pipeline")
                                .runs)
    except KeyError:
        # If this is the first time running this pipeline you don't want
        #  it to fail
        print('No previous runs found, this run produced the highest '
              'number by default.')
        return True
    else:
        for run in pipeline_runs:
            # get the output of the second step
            try:
                multiplied_output_int = (run.get_step("step_2")
                                            .outputs['multiplied_output_int']
                                            .read())
            except KeyError:
                # If you never ran the pipeline or ran it with steps that
                #  don't produce a step with the name
                #  `multiplied_output_int` then you don't want this to fail
                pass
            else:
                if multiplied_output_int > highest_int:
                    highest_int = multiplied_output_int

    if highest_int > input_int:
        print('Previous runs produced a higher number.')
        return False  # There was a past run that produced a higher number
    else:
        print('This run produced the highest number.')
        return True  # The current run produced the highest number

@pipeline
def first_pipeline(
    step_1,
    step_2,
    step_3
):
    output_1, output_2 = step_1()
    output_1, output_2 = step_2(output_1, output_2)
    is_best_run = step_3(output_1)

first_pipeline(step_1=my_first_step(),
               step_2=my_second_step(),
               step_3=my_third_step()).run()
```
</details>

# Class Based API

The class-based ZenML API is defined by the base classes BaseStep and BasePipeline. You'll be subclassing these instead 
of using the `step` and `pipeline` decorators that you have used in the previous sections. These interfaces allow our 
users to maintain a higher level of control while they are creating a step definition and using it within the context of 
a pipeline. 

We'll be using the code for the [Chapter on Runtiem COnfiguration](#configure-at-runtime) as a point of comparison.

### Subclassing the BaseStep

In order to create a step, you will need to create a subclass of the `BaseStep` and implement
its `entrypoint()` method. This entrypoint contains the logic of the step.

{% tabs %}
{% tab title="Class Based API" %}
```python
from zenml.steps import BaseStep, BaseStepConfig, Output

class SecondStepConfig(BaseStepConfig):
    """Trainer params"""
    multiplier: int = 4

    
class SecondStep(BaseStep):
    def entrypoint(
            self,
            config: SecondStepConfig,
            input_int: int,
            input_float: float) -> Output(output_int=int, output_float=float):
        """Step that multiply the inputs"""
        return config.multiplier * input_int, config.multiplier * input_float
```
{% endtab %}
{% tab title="Functional API" %}
```python
from zenml.steps import BaseStepConfig, step, Output
class SecondStepConfig(BaseStepConfig):
    """Trainer params"""
    multiplier: int = 4

@step
def my_second_step(config: SecondStepConfig, input_int: int,
                   input_float: float
                   ) -> Output(output_int=int, output_float=float):
    """Step that multiply the inputs"""
    return config.multiplier * input_int, config.multiplier * input_float
```
{% endtab %}
{% endtabs %}

### Subclassing the BasePipeline

{% tabs %}
{% tab title="Class Based API" %}
```python
from zenml.steps import BaseStep
from zenml.pipelines import BasePipeline


class FirstPipeline(BasePipeline):
    """Pipeline to show off the class-based API"""

    def connect(self,
                step_1: BaseStep,
                step_2: BaseStep) -> None:
        output_1, output_2 = step_1()
        step_2(output_1, output_2)

FirstPipeline(step_1=my_first_step(),
              step_2=SecondStep(SecondStepConfig(multiplier=3))).run()
```
{% endtab %}
{% tab title="Functional API" %}
```python
from zenml.pipelines import pipeline

@pipeline
def first_pipeline(
        step_1,
        step_2
):
    output_1, output_2 = step_1()
    step_2(output_1, output_2)

first_pipeline(step_1=my_first_step(),
               step_2=my_second_step(SecondStepConfig(multiplier=3))
               ).run()
```
{% endtab %}
{% endtabs %}

You can also mix and match the two APIs to your hearts content. Check out the full Code example below to see how.

<details>
    <summary>Minimal Code Example</summary>

```python
from zenml.steps import step, Output, BaseStepConfig, BaseStep
from zenml.pipelines import BasePipeline

@step
def my_first_step() -> Output(output_int=int, output_float=float):
    """Step that returns a pre-defined integer and float"""
    return 7, 0.1

class SecondStepConfig(BaseStepConfig):
    """Trainer params"""
    multiplier: int = 4

class SecondStep(BaseStep):
    def entrypoint(
            self,
            config: SecondStepConfig,
            input_int: int,
            input_float: float) -> Output(output_int=int,
                                          output_float=float):
        """Step that multiply the inputs"""
        return config.multiplier * input_int, config.multiplier * input_float

class FirstPipeline(BasePipeline):
    """Pipeline to show off the class-based API"""

    def connect(self,
                step_1: BaseStep,
                step_2: BaseStep) -> None:
        output_1, output_2 = step_1()
        step_2(output_1, output_2)

FirstPipeline(step_1=my_first_step(),
              step_2=SecondStep(SecondStepConfig(multiplier=3))).run()
```
</details>
