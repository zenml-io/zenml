---
description: Understanding how to configure a ZenML pipeline
---

# Configuring a step and a pipeline

The configuration of a step and/or a pipeline determines various details of how a run is executed. It is an important aspect of running workloads in production, and as such deserves a dedicated section in these docs.

We have already learned about some basics of [configuration in the production guide](../../production-guide/configure-pipeline.md). Here we go into more depth.

## How to apply configuration

Before we learn about all the different configuration, let's briefly look at *how* configuration can be applied to a step or a pipeline. We start with the simplest configuration, a boolean flag called `enable_cache`, that specifies whether caching should be enabled or disabled. There are essentially three ways on you could configure this:

### Method 1: Directly on the decorator

The most basic way to configure a step or a pipeline `@step` and `@pipeline` decorators:

```python
@step(enable_cache=...)
...

@pipeline(enable_cache=...)
...
```

{% hint style="info" %}
Once you set configuration on a pipeline, they will be applied to all steps with some exceptions. See the [later section on precedence for more details](configure-steps-pipelines.md#hierarchy-and-precedence).
{% endhint %}

### Method 2: On the step/pipeline instance

This is exactly the same as passing it through the decorator, but if you prefer you can also pass it in the `configure` methods of the pipeline and step instances:

```python
@step
def my_step() -> None:
    print("my step")


@pipeline
def my_pipeline():
    my_step()


# Same as passing it in the step decorator
my_step.configure(enable_cache=...)

# Same as passing it in the pipeline decorator
my_pipeline.configure(enable_cache=...)
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

The format of a YAML config file is exactly the same as the configurations you would pass in Python in the above two sections. Step-specific configurations can be passed by using the [step invocation ID](managing-steps.md#using-a-custom-step-invocation-id) inside the `steps` dictionary. All keys are optional. Here is an example:

```yaml
# This is equal to @pipeline(enable_cache=True)
enable_cache: True

steps:
  step_invocation_id:
    enable_cache: False  # same as @step(enable_cache=False)
  other_step_invocation_id:
    enable_cache: False  # same as @step(enable_cache=False)
  ...
```

The YAML method is the recommended method on how to apply configuration in production. It has the benefit of being declarative and decoupled from the codebase.

{% hint style="info" %}
It is best practice to put all config files in a `configs` directory at the root of your repository and check them into git history. This way, the tracked commit hash of a pipeline run links back to your config YAML.
{% endhint %}

## Breaking configuration down

Now that we understand how to apply configuration, let's see all the various ways we can configure a ZenML pipeline. We will use the YAML configuration for this, but as [seen in the section above](#how-to-apply-configuration), you can use the information here to configure your steps and pipelines any way you choose.

First, let's create a simple pipeline:

```python
% run.py
from zenml import step, pipeline

@step
def generate_number() -> int:
    return 1

@step
def add_two_numbers(num1: int, num2: int) -> int:
    return num1 + num2

@pipeline
def addition_pipeline():
    generated = generate_number()
    result = add_two_numbers(num1=2, num2=generated)

# Executable trigger for the pipeline if running this python script directly.
if __name__=="__main__":
    # This function writes 
    addition_pipeline.write_run_configuration_template(path='run.yaml')
    addition_pipeline()
```

The method `write_run_configuration_template` genreates a config template (at path `run.yaml` in this case) that includes all configuration options for this specific pipeline and your active stack. Let's run the pipeline:

```python
python run.py
```

<details>

<summary>An example of a generated YAML configuration template</summary>

```yaml
build: Union[PipelineBuildBase, UUID, NoneType]
enable_artifact_metadata: Optional[bool]
enable_artifact_visualization: Optional[bool]
enable_cache: Optional[bool]
enable_step_logs: Optional[bool]
extra: Mapping[str, Any]
model_version:
  audience: Optional[str]
  description: Optional[str]
  ethics: Optional[str]
  license: Optional[str]
  limitations: Optional[str]
  name: str
  save_models_to_registry: bool
  suppress_class_validation_warnings: bool
  tags: Optional[List[str]]
  trade_offs: Optional[str]
  use_cases: Optional[str]
  version: Union[ModelStages, int, str, NoneType]
  was_created_in_this_run: bool
parameters: Optional[Mapping[str, Any]]
run_name: Optional[str]
schedule:
  catchup: bool
  cron_expression: Optional[str]
  end_time: Optional[datetime]
  interval_second: Optional[timedelta]
  name: Optional[str]
  start_time: Optional[datetime]
settings:
  docker:
    apt_packages: List[str]
    build_context_root: Optional[str]
    build_options: Mapping[str, Any]
    copy_files: bool
    copy_global_config: bool
    dockerfile: Optional[str]
    dockerignore: Optional[str]
    environment: Mapping[str, Any]
    install_stack_requirements: bool
    parent_image: Optional[str]
    replicate_local_python_environment: Union[List[str], PythonEnvironmentExportMethod,
      NoneType]
    required_hub_plugins: List[str]
    required_integrations: List[str]
    requirements: Union[NoneType, str, List[str]]
    skip_build: bool
    source_files: SourceFileMode
    target_repository: str
    user: Optional[str]
  resources:
    cpu_count: Optional[PositiveFloat]
    gpu_count: Optional[NonNegativeInt]
    memory: Optional[ConstrainedStrValue]
steps:
  add_two_numbers:
    enable_artifact_metadata: Optional[bool]
    enable_artifact_visualization: Optional[bool]
    enable_cache: Optional[bool]
    enable_step_logs: Optional[bool]
    experiment_tracker: Optional[str]
    extra: Mapping[str, Any]
    failure_hook_source:
      attribute: Optional[str]
      module: str
      type: SourceType
    model_version:
      audience: Optional[str]
      description: Optional[str]
      ethics: Optional[str]
      license: Optional[str]
      limitations: Optional[str]
      name: str
      save_models_to_registry: bool
      suppress_class_validation_warnings: bool
      tags: Optional[List[str]]
      trade_offs: Optional[str]
      use_cases: Optional[str]
      version: Union[ModelStages, int, str, NoneType]
      was_created_in_this_run: bool
    name: Optional[str]
    outputs:
      output:
        default_materializer_source:
          attribute: Optional[str]
          module: str
          type: SourceType
        materializer_source: Optional[Tuple[Source, ...]]
    parameters: {}
    settings:
      docker:
        apt_packages: List[str]
        build_context_root: Optional[str]
        build_options: Mapping[str, Any]
        copy_files: bool
        copy_global_config: bool
        dockerfile: Optional[str]
        dockerignore: Optional[str]
        environment: Mapping[str, Any]
        install_stack_requirements: bool
        parent_image: Optional[str]
        replicate_local_python_environment: Union[List[str], PythonEnvironmentExportMethod,
          NoneType]
        required_hub_plugins: List[str]
        required_integrations: List[str]
        requirements: Union[NoneType, str, List[str]]
        skip_build: bool
        source_files: SourceFileMode
        target_repository: str
        user: Optional[str]
      resources:
        cpu_count: Optional[PositiveFloat]
        gpu_count: Optional[NonNegativeInt]
        memory: Optional[ConstrainedStrValue]
    step_operator: Optional[str]
    success_hook_source:
      attribute: Optional[str]
      module: str
      type: SourceType
  generate_number:
    enable_artifact_metadata: Optional[bool]
    enable_artifact_visualization: Optional[bool]
    enable_cache: Optional[bool]
    enable_step_logs: Optional[bool]
    experiment_tracker: Optional[str]
    extra: Mapping[str, Any]
    failure_hook_source:
      attribute: Optional[str]
      module: str
      type: SourceType
    model_version:
      audience: Optional[str]
      description: Optional[str]
      ethics: Optional[str]
      license: Optional[str]
      limitations: Optional[str]
      name: str
      save_models_to_registry: bool
      suppress_class_validation_warnings: bool
      tags: Optional[List[str]]
      trade_offs: Optional[str]
      use_cases: Optional[str]
      version: Union[ModelStages, int, str, NoneType]
      was_created_in_this_run: bool
    name: Optional[str]
    outputs:
      output:
        default_materializer_source:
          attribute: Optional[str]
          module: str
          type: SourceType
        materializer_source: Optional[Tuple[Source, ...]]
    parameters: {}
    settings:
      docker:
        apt_packages: List[str]
        build_context_root: Optional[str]
        build_options: Mapping[str, Any]
        copy_files: bool
        copy_global_config: bool
        dockerfile: Optional[str]
        dockerignore: Optional[str]
        environment: Mapping[str, Any]
        install_stack_requirements: bool
        parent_image: Optional[str]
        replicate_local_python_environment: Union[List[str], PythonEnvironmentExportMethod,
          NoneType]
        required_hub_plugins: List[str]
        required_integrations: List[str]
        requirements: Union[NoneType, str, List[str]]
        skip_build: bool
        source_files: SourceFileMode
        target_repository: str
        user: Optional[str]
      resources:
        cpu_count: Optional[PositiveFloat]
        gpu_count: Optional[NonNegativeInt]
        memory: Optional[ConstrainedStrValue]
    step_operator: Optional[str]
    success_hook_source:
      attribute: Optional[str]
      module: str
      type: SourceType
```

</details>

The generated config contains most configuration available for this pipeline. Let's walk through it section by section: 

### `enable_XXX` parameters

enable_artifact_metadata: Optional[bool]
enable_artifact_visualization: Optional[bool]
enable_cache: Optional[bool]
enable_step_logs: Optional[bool]

### `build` ID

### `extra` dict

You might have noticed another dictionary that is available to be passed to steps and pipelines called `extra`. This dictionary is meant to be used to pass any configuration down to the pipeline, step, or stack components that the user has use of.

An example of this is if I want to tag a pipeline, I can do the following:

### Configuring the `model_version`

### Pipeline and step `parameters`

### Setting the `run_name`

### Real-time `settings`

Read more in the [dedicated section on settings](pipeline-settings.md).

### Step-specific configuration

A lot of pipeline-level configuration can also be applied at a step level (as we already seen with the `enable_cache` flag). However, there is some configuration that is step-specific, meaning it cannot be applied at a pipeline level, but only at a step level.

* `experiment_tracker`
* `step_operator`
* `failure_hook_source`
* `outputs`
* `success_hook_source`

Read more in the [dedicated section on managing steps](managing-steps.md).

## Hierarchy and precedence

Some settings can be configured on pipelines and steps, some only on one of the two. Pipeline-level settings will be automatically applied to all steps, but if the same setting is configured on a step as well that takes precedence. The next section explains in more detail how the step-level settings will be merged with pipeline settings.

## Merging settings on instance/run:

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


## Fetching configuration

Any configuration can be fetched using the [client from the Python SDK](../../../reference/python-client.md). For example, say we use the `extra` parameter to tag a pipeline:

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

The configuration is also displayed in the dashboard in the pipeline run details page.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
