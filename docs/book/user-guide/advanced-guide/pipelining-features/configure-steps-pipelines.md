---
description: Configuring pipelines, steps, and stack components in ZenML.
---

# Configure steps/pipelines

## Define steps

To define a step, all you need to do is decorate your Python functions with ZenML's `@step` decorator:

```python
from zenml import step

@step
def my_function():
    ...
```

### Type annotations

Your functions will work as ZenML steps even if you don't provide any type annotations for their inputs and outputs. However, adding type annotations to your step functions gives you lots of additional benefits:

* **Type validation of your step inputs**: ZenML makes sure that your step functions receive an object of the correct type from the upstream steps in your pipeline.
* **Better serialization**: Without type annotations, ZenML uses [Cloudpickle](https://github.com/cloudpipe/cloudpickle) to serialize your step outputs. When provided with type annotations, ZenML can choose a [materializer](../../../getting-started/core-concepts.md#materializers) that is best suited for the output. In case none of the builtin materializers work, you can even [write a custom materializer](../data-management/handle-custom-data-types.md).

```python
from typing import Tuple
from zenml import step

@step
def square_root(number: int) -> float:
    return number ** 0.5

# To define a step with multiple outputs, use a `Tuple` type annotation
@step
def divide(a: int, b: int) -> Tuple[int, int]:
    return a // b, a % b
```

{% hint style="info" %}
It is impossible for ZenML to detect whether you want your step to have a single output artifact of type `Tuple` or multiple output artifacts just by looking at the type annotation.

We use the following convention to differentiate between the two: When the `return` statement is followed by a tuple literal (e.g. `return 1, 2` or `return (value_1, value_2)`) we treat it as a step with multiple outputs. All other cases are treated as a step with a single output of type `Tuple`.

```python
# Single output artifact
@step
def my_step() -> Tuple[int, int]:
    output_value = (0, 1)
    return output_value

# Single output artifact with variable length
@step
def my_step(condition) -> Tuple[int, ...]:
    if condition:
        output_value = (0, 1)
    else:
        output_value = (0, 1, 2)

    return output_value

# Single output artifact using the `Annotated` annotation
@step
def my_step() -> Annotated[Tuple[int, ...], "my_output"]:
    return 0, 1


# Multiple output artifacts
@step
def my_step() -> Tuple[int, int]:
    return 0, 1


# Not allowed: Variable length tuple annotation when using
# multiple output artifacts
@step
def my_step() -> Tuple[int, ...]:
    return 0, 1
```
{% endhint %}

If you want to make sure you get all the benefits of type annotating your steps, you can set the environment variable `ZENML_ENFORCE_TYPE_ANNOTATIONS` to `True`. ZenML will then raise an exception in case one of the steps you're trying to run is missing a type annotation.

### Step output names

By default, ZenML uses the output name `output` for single output steps and `output_0, output_1, ...` for steps with multiple outputs. These output names are used to display your outputs in the dashboard and [fetch them after your pipeline is finished](../../starter-guide/fetching-pipelines.md).

If you want to use custom output names for your steps, use the `Annotated` type annotation:

```python
from typing_extensions import Annotated  # or `from typing import Annotated on Python 3.9+
from typing import Tuple
from zenml import step

@step
def square_root(number: int) -> Annotated[float, "custom_output_name"]:
    return number ** 0.5

@step
def divide(a: int, b: int) -> Tuple[
    Annotated[int, "quotient"],
    Annotated[int, "remainder"]
]:
    return a // b, a % b
```

{% hint style="info" %}
If you do not give your outputs custom names, the created artifacts will be named `{pipeline_name}::{step_name}::output` or `{pipeline_name}::{step_name}::output_{i}` in the dashboard. See the [documentation on artifact versioning and configuration](../../starter-guide/manage-artifacts.md) for more information.
{% endhint %}

## Configure steps/pipelines

### Parameters for your steps

When calling a step in a pipeline, the inputs provided to the step function can either be an **artifact** or a **parameter**. An artifact represents the output of another step that was executed as part of the same pipeline and serves as a means to share data between steps. Parameters, on the other hand, are values provided explicitly when invoking a step. They are not dependent on the output of other steps and allow you to parameterize the behavior of your steps.

{% hint style="info" %}
In order to allow the configuration of your steps using a configuration file, only values that can be serialized to JSON using Pydantic can be passed as parameters. If you want to pass other non-JSON-serializable objects such as NumPy arrays to your steps, use [External Artifacts](../../starter-guide/manage-artifacts.md#passing-artifacts-to-a-downstream-pipeline) instead.
{% endhint %}

```python
@step
def my_step(input_1: int, input_2: int) -> None:
    pass


@pipeline
def my_pipeline():
    int_artifact = some_other_step()
    # We supply the value of `input_1` as an artifact and
    # `input_2` as a parameter
    my_step(input_1=int_artifact, input_2=42)
    # We could also call the step with two artifacts or two
    # parameters instead:
    # my_step(input_1=int_artifact, input_2=int_artifact)
    # my_step(input_1=1, input_2=2)
```

Parameters of steps and pipelines can also be passed in using YAML configuration files. Following configuration file and python code can work together and give you the flexibility to update configuration only in YAML file, once needed:
```yaml
# config.yaml

# these are parameters of the pipeline
parameters:
  environment: production

steps:
  my_step:
    # these are parameters of the step `my_step`
    parameters:
      input_2: 42
```

```python
@step
def my_step(input_1: int, input_2: int) -> None:
    pass

# input `environment` will come from the configuration file
# and it is evaluated to `production`
@pipeline
def my_pipeline(environment: str):
    # We supply value of `environment` from pipeline inputs
    int_artifact = some_other_step(environment=environment)
    # We supply the value of `input_1` as an artifact and
    # `input_2` is coming from the configuration file
    my_step(input_1=int_artifact)

if __name__=="__main__":
    my_pipeline.with_options(config_paths="config.yaml")()
```
{% hint style="warning" %}
There might be conflicting settings for step or pipeline inputs, while working with YAML configuration files. Such situations happen when you define a step or a pipeline parameter in the configuration file and override it from the code later on. Don't worry - once it happens you will be informed with details and instruction on how to fix.
Example of such a conflict:
```yaml
# config.yaml
parameters:
    some_param: 24

steps:
  my_step:
    parameters:
      input_2: 42
```
```python
# run.py
@step
def my_step(input_1: int, input_2: int) -> None:
    pass

@pipeline
def my_pipeline(some_param: int):
    # here an error will be raised since `input_2` is
    # `42` in config, but `43` was provided in the code
    my_step(input_1=42, input_2=43)

if __name__=="__main__":
    # here an error will be raised since `some_param` is
    # `24` in config, but `23` was provided in the code
    my_pipeline(23)
```
{% endhint %}

**Parameters and caching**

When an input is passed as a parameter, the step will only be cached if all parameter values are exactly the same as for previous executions of the step.

**Artifacts and caching**

When an artifact is used as a step function input, the step will only be cached if all the artifacts are exactly the same as for previous executions of the step. This means that if any of the upstream steps that produce the input artifacts for a step were not cached, the step itself will always be executed.

### Using a custom step invocation ID

When calling a ZenML step as part of your pipeline, it gets assigned a unique **invocation ID** that you can use to reference this step invocation when [defining the execution order](configure-steps-pipelines.md#control-the-execution-order) of your pipeline steps or use it to [fetch information](../../starter-guide/fetching-pipelines.md) about the invocation after the pipeline has finished running.

```python
from zenml import pipeline, step

@step
def my_step() -> None:
    ...

@pipeline
def example_pipeline():
    # When calling a step for the first time inside a pipeline,
    # the invocation ID will be equal to the step name -> `my_step`.
    my_step()
    # When calling the same step again, the suffix `_2`, `_3`, ... will
    # be appended to the step name to generate a unique invocation ID.
    # For this call, the invocation ID would be `my_step_2`.
    my_step()
    # If you want to use a custom invocation ID when calling a step, you can
    # do so by passing it like this. If you pass a custom ID, it needs to be
    # unique for all the step invocations that happen as part of this pipeline.
    my_step(id="my_custom_invocation_id")
```

### Control the execution order

By default, ZenML uses the data flowing between steps of your pipeline to determine the order in which steps get executed.

The following example shows a pipeline in which `step_3` depends on the outputs of `step_1` and `step_2`. This means that ZenML can execute both `step_1` and `step_2` in parallel but needs to wait until both are finished before `step_3` can be started.

```python
from zenml import pipeline

@pipeline
def example_pipeline():
    step_1_output = step_1()
    step_2_output = step_2()
    step_3(step_1_output, step_2_output)
```

If you have additional constraints on the order in which steps get executed, you can specify non-data dependencies by passing the invocation IDs of steps that should run before your step like this: `my_step(after="other_step")`. If you want to define multiple upstream steps, you can also pass a list for the `after` argument when calling your step: `my_step(after=["other_step", "other_step_2"])`.

{% hint style="info" %}
Check out the [previous section](configure-steps-pipelines.md#using-a-custom-step-invocation-id) to learn about the invocation ID and how to use a custom one for your steps.
{% endhint %}

```python
from zenml import pipeline

@pipeline
def example_pipeline():
    step_1_output = step_1(after="step_2")
    step_2_output = step_2()
    step_3(step_1_output, step_2_output)
```

This pipeline is similar to the one explained above, but this time ZenML will make sure to only start `step_1` after `step_2` has finished.

### Enable or disable logs storing

By default, ZenML uses a special logging handler to capture the logs that occur during the execution of a step. These logs are stored within the respective artifact store of your stack.

```python
import logging

from zenml import step

@step 
def my_step() -> None:
    logging.warning("`Hello`")  # You can use the regular `logging` module.
    print("World.")  # You can utilize `print` statements as well. 
```

You can display the logs in the dashboard as follows:

![Displaying step logs on the dashboard](../../../.gitbook/assets/zenml\_step\_logs.png)

If you do not want to store the logs in your artifact store, you can:

1.  Disable it by using the `enable_step_logs` parameter either with your `@pipeline` or `@step` decorator:

    ```python
    from zenml import pipeline, step

    @step(enable_step_logs=False)  # disables logging for this step
    def my_step() -> None:
        ...

    @pipeline(enable_step_logs=False)  # disables logging for the entire pipeline
    def my_pipeline():
        ...
    ```
2. Disable it by using the environmental variable `ZENML_DISABLE_STEP_LOGS_STORAGE`. This environmental variable takes precedence over the parameters mentioned above.

## Settings in ZenML

Settings in ZenML allow you to configure runtime configurations for stack components and pipelines. Concretely, they allow you to configure:

* The [resources](../environment-management/scale-compute-to-the-cloud.md#specify-resource-requirements-for-steps) required for a step
* Configuring the [containerization](../environment-management/containerize-your-pipeline.md) process of a pipeline (e.g. What requirements get installed in the Docker image)
* Stack component-specific configuration, e.g., if you have an experiment tracker passing in the name of the experiment at runtime

You will learn about all of the above in more detail later, but for now, let's try to understand that all of this configuration flows through one central concept, called `BaseSettings` (From here on, we use `settings` and `BaseSettings` as analogous in this guide).

### Types of settings

Settings are categorized into two types:

* **General settings** that can be used on all ZenML pipelines. Examples of these are:
  * [`DockerSettings`](../environment-management/containerize-your-pipeline.md) to specify docker settings.
  * [`ResourceSettings`](../environment-management/scale-compute-to-the-cloud.md#specify-resource-requirements-for-steps) to specify resource settings.
* **Stack-component-specific settings**: These can be used to supply runtime configurations to certain stack components (key= \<COMPONENT\_CATEGORY>.\<COMPONENT\_FLAVOR>). Settings for components not in the active stack will be ignored. Examples of these are:
  * [`KubeflowOrchestratorSettings`](../../../stacks-and-components/component-guide/orchestrators/kubeflow.md) to specify Kubeflow settings.
  * [`MLflowExperimentTrackerSettings`](../../../stacks-and-components/component-guide/experiment-trackers/mlflow.md) to specify MLflow settings.
  * [`WandbExperimentTrackerSettings`](../../../stacks-and-components/component-guide/experiment-trackers/wandb.md) to specify W\&B settings.
  * [`WhylogsDataValidatorSettings`](../../../stacks-and-components/component-guide/data-validators/whylogs.md) to specify Whylogs settings.

For stack-component-specific settings, you might be wondering what the difference is between these and the configuration passed in while doing `zenml stack-component register <NAME> --config1=configvalue --config2=configvalue`, etc. The answer is that the configuration passed in at registration time is static and fixed throughout all pipeline runs, while the settings can change.

A good example of this is the [`MLflow Experiment Tracker`](../../../stacks-and-components/component-guide/experiment-trackers/mlflow.md), where configuration which remains static such as the `tracking_url` is sent through at registration time, while runtime configuration such as the `experiment_name` (which might change every pipeline run) is sent through as runtime settings.

Even though settings can be overridden at runtime, you can also specify _default_ values for settings while configuring a stack component. For example, you could set a default value for the `nested` setting of your MLflow experiment tracker: `zenml experiment-tracker register <NAME> --flavor=mlflow --nested=True`

This means that all pipelines that run using this experiment tracker use nested MLflow runs unless overridden by specifying settings for the pipeline at runtime.

{% embed url="https://www.youtube.com/embed/AdwW6DlCWFE" %}
Stack Component Config vs Settings in ZenML
{% endembed %}

**Using objects or dicts**

Settings can be passed in directly as BaseSettings-subclassed objects, or a dictionary representation of the object. For example, a Docker configuration can be passed in as follows:

```python
from zenml.config import DockerSettings

settings = {'docker': DockerSettings(requirements=['pandas'])}
```

Or like this:

```python
settings = {'docker': {'requirements': ['pandas']}}
```

### Utilizing the settings

#### Method 1: Directly on the decorator

The most basic way to set settings is through the `settings` variable that exists in both `@step` and `@pipeline` decorators:

```python
@step(settings=...)


...


@pipeline(settings=...)


...
```

{% hint style="info" %}
Once you set settings on a pipeline, they will be applied to all steps with some exceptions. See the [later section on precedence for more details](configure-steps-pipelines.md#hierarchy-and-precedence).
{% endhint %}

#### Method 2: On the step/pipeline instance

This is exactly the same as passing it through the decorator, but if you prefer you can also pass it in the `configure` methods of the pipeline and step instances:

```python
@step
def my_step() -> None:
    print("my step")


@pipeline
def my_pipeline():
    my_step()


# Same as passing it in the step decorator
my_step.configure(settings=...)

# Same as passing it in the pipeline decorator
my_pipeline.configure(settings=...)
```

#### Method 3: Configuring with YAML

As all settings can be passed through as a dictionary, users have the option to send all configurations in via a YAML file. This is useful in situations where code changes are not desirable.

To use a YAML file, you must pass it to the `with_options(...)` method of a pipeline:

```python
@step
def my_step() -> None:
    print("my step")


@pipeline
def my_pipeline():
    my_step()


# Pass in a config file
my_pipeline = my_pipeline.with_options(config_path='/local/path/to/config.yaml')
```

The format of a YAML config file is exactly the same as the configurations you would pass in Python in the above two sections. Step-specific configurations can be passed by using the [step invocation ID](configure-steps-pipelines.md#using-a-custom-step-invocation-id) inside the `steps` dictionary. Here is a rough skeleton of a valid YAML config. All keys are optional.

```yaml
enable_cache: True
enable_artifact_metadata: True
enable_artifact_visualization: True
extra:
  tags: production
run_name: my_run
schedule: { }
settings: { }  # same as pipeline settings
steps:
  step_invocation_id:
    settings: { }  # same as step settings
  other_step_invocation_id:
    settings: { }
  ...
```

You can also use the following method to generate a config template (at path `/local/path/to/config.yaml`) that includes all configuration options for this specific pipeline and your active stack:

```python
my_pipeline.write_run_configuration_template(path='/local/path/to/config.yaml')
```

Here is an example of a YAML config file generated from the above method:

<details>

<summary>An example of a YAML config</summary>

Some configuration is commented out as it is not needed.

```yaml
enable_cache: True
enable_artifact_metadata: True
enable_artifact_visualization: True
extra:
  tags: production
run_name: my_run
# schedule:
#   catchup: bool
#   cron_expression: Optional[str]
#   end_time: Optional[datetime]
#   interval_second: Optional[timedelta]
#   start_time: Optional[datetime]
settings:
  docker:
    build_context_root: .
    # build_options: Mapping[str, Any]
    # source_files: str
    # copy_global_config: bool
    # dockerfile: Optional[str]
    # dockerignore: Optional[str]
    # environment: Mapping[str, Any]
    # install_stack_requirements: bool
    # parent_image: Optional[str]
    # replicate_local_python_environment: Optional
    # required_integrations: List[str]
    requirements:
      - pandas
    # target_repository: str
    # user: Optional[str]
  resources:
    cpu_count: 1
    gpu_count: 1
    memory: "1GB"
steps:
  get_first_num:
    enable_cache: false
    experiment_tracker: mlflow_tracker
#     extra: Mapping[str, Any]
#     outputs:
#       first_num:
#         artifact_source: Optional[str]
#         materializer_source: Optional[str]
#     parameters: {}
#     settings:
#       resources:
#         cpu_count: Optional[PositiveFloat]
#         gpu_count: Optional[PositiveInt]
#         memory: Optional[ConstrainedStrValue]
#     step_operator: Optional[str]
#   get_random_int:
#     enable_cache: Optional[bool]
#     experiment_tracker: Optional[str]
#     extra: Mapping[str, Any]
#     outputs:
#       random_num:
#         artifact_source: Optional[str]
#         materializer_source: Optional[str]
#     parameters: {}
#     settings:
#       resources:
#         cpu_count: Optional[PositiveFloat]
#         gpu_count: Optional[PositiveInt]
#         memory: Optional[ConstrainedStrValue]
#     step_operator: Optional[str]
#   subtract_numbers:
#     enable_cache: Optional[bool]
#     experiment_tracker: Optional[str]
#     extra: Mapping[str, Any]
#     outputs:
#       result:
#         artifact_source: Optional[str]
#         materializer_source: Optional[str]
#     parameters: {}
#     settings:
#       resources:
#         cpu_count: Optional[PositiveFloat]
#         gpu_count: Optional[PositiveInt]
#         memory: Optional[ConstrainedStrValue]
#     step_operator: Optional[str]
```

</details>

#### The `extra` dict

You might have noticed another dictionary that is available to be passed to steps and pipelines called `extra`. This dictionary is meant to be used to pass any configuration down to the pipeline, step, or stack components that the user has use of.

An example of this is if I want to tag a pipeline, I can do the following:

```python
@pipeline(name='my_pipeline', extra={'tag': 'production'})


...
```

This tag is now associated and tracked with all pipeline runs, and can be [fetched later](../../starter-guide/fetching-pipelines.md):

```python
from zenml.client import Client

pipeline_run = Client().get_pipeline_run("<PIPELINE_RUN_NAME>")

# print out the extra
print(pipeline_run.config.extra)
# {'tag': 'production'}
```

#### Hierarchy and precedence

Some settings can be configured on pipelines and steps, some only on one of the two. Pipeline-level settings will be automatically applied to all steps, but if the same setting is configured on a step as well that takes precedence. The next section explains in more detail how the step-level settings will be merged with pipeline settings.

#### Merging settings on instance/run:

When a settings object is configured, ZenML merges the values with previously configured keys. E.g.:

```python
from zenml.config import ResourceSettings


@step(settings={"resources": ResourceSettings(cpu_count=2, memory="1GB")})
def my_step() -> None:
    ...


my_step.configure(
    settings={"resources": ResourceSettings(gpu_count=1, memory="2GB")}
)

my_step.configuration.settings["resources"]
# cpu_count: 2, gpu_count=1, memory="2GB"
```

In the above example, the two settings were automatically merged.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
