---
description: Configure Step and Pipeline Parameters for Each Run.
---

# Runtime Configuration

A ZenML pipeline clearly separates business logic from parameter configuration.
Business logic is what defines
a step and the pipeline. Step and pipeline configurations are used to
dynamically set parameters at runtime.

## Step configuration

You can easily add a configuration to a step by creating your configuration as a
subclass to the BaseStepConfig.
When such a config object is passed to a step, it is not treated like other
artifacts. Instead, it gets passed
into the step when the pipeline is instantiated.

```python
from zenml.steps import step, Output, BaseStepConfig


class SecondStepConfig(BaseStepConfig):
    """Trainer params"""
    multiplier: int = 4


@step
def my_second_step(config: SecondStepConfig, input_int: int, input_float: float
                   ) -> Output(output_int=int, output_float=float):
    """Step that multiply the inputs"""
    return config.multiplier * input_int, config.multiplier * input_float
```

The default value for the multiplier is set to 4. However, when the pipeline is
instantiated you can
override the default like this:

```python
first_pipeline(step_1=my_first_step(),
               step_2=my_second_step(SecondStepConfig(multiplier=3))
               ).run()
```

This functionality is based on [Step Fixtures](#step-fixtures) which you will
learn more about below.

### Setting step parameters using a config file

In addition to setting parameters for your pipeline steps in code as seen above,
ZenML also allows you to use a
configuration [YAML](https://yaml.org) file. This configuration file must follow
the following structure:

```yaml
steps:
  step_name:
    parameters:
      parameter_name: parameter_value
      some_other_parameter_name: 2
  some_other_step_name:
    ...
```

For our example from above this results in the following configuration
yaml.&#x20;

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

## Run from CLI

In case you want to have control to configure and run your pipeline from outside
your code. For this you can use the
ZenML command line argument:

```shell
zenml pipeline run <NAME-OF-PYTHONFILE> -c <NAME-OF-CONFIG-YAML-FILE>
```

{% hint style="warning" %}
Do **not** instantiate and run your pipeline within the python file that you
want to run using the CLI, else your
pipeline will be run twice, possibly with different configurations.
{% endhint %}

This will require a config file with a bit more information than how it is
described above.

### Define the name of the pipeline definition

You will need to define which pipeline to run by it's name.

```yaml
name: <name_of_your_pipeline>
...
```

In case you defined your pipeline using decorators this name is the name of the
decorated function. If you used the
[Class Based API](#class-based-api), it will be the name of your class.

```python
from zenml.pipelines import pipeline, BasePipeline


@pipeline
def name_of_your_pipeline(...):
    ...


class ClassBasedPipelineName(BasePipeline):
    ...
```

### Supply the names of the step functions (and materializers)

In total the step functions can be supplied with 3 arguments here:

* source:
    * name of the step
      *(Optional) file of the step (file contains the step)

```yaml
  steps:
    step_1:
      source:
        name: <step_name>
        file: <relative/filepath>  
```

* parameters - list of parameters for the StepConfig
* materializers - dict of output_name and corresponding Materializer name and
  file

{% hint style="info" %}
Materializers are responsible for reading and writing. You can learn more about
Materializers in the
[materializer section](materializer.md).
{% endhint %}

```yaml
...
steps:
  ...
  step_2:
    source:
      name: <step_name>
    parameters:
      multiplier: 3
    materializers:
      output_obj:
        name: <MaterializerName>
        file: <relative/filepath>
```

Again the step name corresponds to the function or class name of your step. The
materializer name refers to the class name of your materializer.

```python
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.steps import step


class MaterializerName(BaseMaterializer):
    ...


@step
def step_name(...):
    ...
```

### When you put it all together you would have something that looks like this:

{% tabs %}
{% tab title="CLI Command" %}

```shell
zenml pipeline run run.py -c config.yaml
```

{% endtab %}
{% tab title="config.yaml" %}

```yaml
name: first_pipeline
steps:
  step_1:
    source:
      name: my_first_step
  step_2:
    source:
      name: my_second_step
    parameters:
      multiplier: 3
    materializers:
      output_obj:
        name: MyMaterializer
```

{% endtab %}
{% tab title="run.py" %}

```python
import os
from typing import Type

from zenml.artifacts import DataArtifact
from zenml.io import fileio
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.steps import step, Output, BaseStepConfig
from zenml.pipelines import pipeline


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
def my_first_step() -> Output(output_int=int, output_float=float):
    """Step that returns a pre-defined integer and float"""
    return 7, 0.1


class SecondStepConfig(BaseStepConfig):
    """Trainer params"""
    multiplier: int = 4


@step
def my_second_step(config: SecondStepConfig, input_int: int,
                   input_float: float
                   ) -> Output(output_int=int,
                               output_float=float,
                               output_obj=MyObj):
    """Step that multiply the inputs"""
    return (config.multiplier * input_int,
            config.multiplier * input_float,
            MyObj("Custom-Object"))


@pipeline(enable_cache=False)
def first_pipeline(
        step_1,
        step_2
):
    output_1, output_2 = step_1()
    step_2(output_1, output_2)
```

{% endtab %}
{% tab title="Equivalent run from python" %}
This is what the same pipeline run would look like if triggered from within
python.

```python
first_pipeline(
    step_1=my_first_step(),
    step_2=(my_second_step(SecondStepConfig(multiplier=3))
            .with_return_materializers({"output_obj": MyMaterializer}))
).run()
```

{% endtab %}
{% endtabs %}

{% hint style="info" %}
Pro-Tip: You can easily use this to configure and run your pipeline from within
your
[github action](https://docs.github.com/en/actions) (or comparable tools). This
way you ensure each run is directly
associated with an associated code version.
{% endhint %}

## Pipeline Run Name

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

### Summary in Code

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
