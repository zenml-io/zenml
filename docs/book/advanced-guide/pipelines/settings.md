---
description: Configuring pipelines, steps, and stack components in ZenML.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Settings in ZenML

## Video Tutorial

{% embed url="https://www.youtube.com/embed/hI-UNV7uoNI" %} Configuring pipelines, steps, and stack components in ZenML {% endembed %}

This video gives an overview of everything discussed in this chapter.

## Settings in ZenML

As discussed in a [previous chapter](../../starter-guide/pipelines/parameters-and-caching.md), there are two ways to configure anything in ZenML:

- `BaseParameters`: Runtime configuration passed down as a parameter to step functions.
- `BaseSettings`: Runtime settings passed down to stack components and pipelines.

We have [already discussed `BaseParameters`](../../starter-guide/pipelines/parameters-and-caching.md) and now is the time to talk about its brother, `BaseSettings`.

### What can be configured?

Looked at one way, `BaseParameters` configure steps within a pipeline to behave in a different way during runtime. But what other
things can be configured at runtime? Here is a list:

- The [resources](./step-resources.md) of a step.
- Configuring the [containerization](../../starter-guide/production-fundamentals/containerization.md) process of a pipeline (e.g. What requirements get installed in the Docker image).
- Stack component specific configuration, e.g., if you have an experiment tracker passing in the name of the experiment at runtime.

You will learn about all of the above in more detail later, but for now,
let's try to understand that all of this configuration flows through one central concept, called `BaseSettings` (From here on, we use `settings` and `BaseSettings` as analogous in this guide).

### Types of settings

Settings are categorized into two types:

- **General settings** that can be used on all ZenML pipelines. Examples of these are:
  - [`DockerSettings`](../../starter-guide/production-fundamentals/containerization.md) to specify docker settings.
  - [`ResourceSettings`](./step-resources.md) to specify resource settings.
- **Stack component specific settings**: These can be used to supply runtime configurations to certain stack components (key= <COMPONENT_CATEGORY>.<COMPONENT_FLAVOR>). Settings for components not in the active stack will be ignored. Examples of these are:
  - [`KubeflowOrchestratorSettings`](../../component-gallery/orchestrators/kubeflow.md) to specify Kubeflow settings.
  - [`MLflowExperimentTrackerSettings`](../../component-gallery/experiment-trackers/mlflow.md) to specify MLflow settings.
  - [`WandbExperimentTrackerSettings`](../../component-gallery/experiment-trackers/wandb.md) to specify W&B settings.
  - [`WhylogsDataValidatorSettings`](../../component-gallery/data-validators/whylogs.md) to specify Whylogs settings.

For stack component specific settings, you might be wondering what the difference is between these and the configuration passed in while doing `zenml stack-component register <NAME> --config1=configvalue --config2=configvalue` etc.
The answer is that the configuration passed in at registration time is static and fixed throughout all pipeline runs, while the settings can change.

A good example of this is the [`MLflow Experiment Tracker`](../../component-gallery/experiment-trackers/mlflow.md), where configuration which remains static such as the `tracking_url` is sent through at registration time, while runtime configuration such as the `experiment_name` (which might change every pipeline run) is sent through as runtime settings.

Even though settings can be overridden at runtime, you can also specify *default* values for settings while configuring a stack component. For example, you could set a default value for the `nested` setting of your MLflow experiment tracker:
`zenml experiment-tracker register <NAME> --flavor=mlflow --nested=True`

This means that all pipelines that run using this experiment tracker use nested MLflow runs unless overridden by specifying settings for the pipeline at runtime.

{% embed url="https://www.youtube.com/embed/AdwW6DlCWFE" %} Stack Component Config vs Settings in ZenML {% endembed %}

#### Using objects or dicts

Settings can be passed in directly as BaseSettings-subclassed objects, or a dict-representation of the object. For example, a Docker configuration can be passed in as follows:

```python
from zenml.config import DockerSettings

settings={'docker': DockerSettings(requirements=['pandas'])}
```

Or like this:

```python
settings={'docker': {'requirements': ['pandas']}}
```

### How to use settings

#### Method 1: Directly on the decorator

The most basic way to set settings is through the `settings` variable
that exists in both `@step` and `@pipeline` decorators:

```python
@step(settings=...)
  ...

@pipeline(settings=...)
  ...
```

{% hint style="info" %}
Once you set settings on a pipeline, they will be applied to all steps with some exception. See the [later section on precedence for more details](#hierarchy-and-precedence).
{% endhint %}

#### Method 2: On the step/pipeline instance

This is exactly the same as passing it through the decorator, but if you prefer you can also pass it in the `configure` methods of the pipeline and step instances:

```python
@step
def my_step() -> None:
  print("my step")

@pipeline
def my_pipeline(step1):
  step1()

# Same as passing it in the step decorator
step_instance = my_step().configure(settings=...)

pipeline_instance = my_pipeline(
  step1 = step_instance
)

# Same as passing it in the pipeline decorator
pipeline_instance.configure(settings=...)

# Or you can pass it in the run function
pipeline_instance.run(settings=...)
```

#### Method 3: Configuring with YAML

As all settings can be passed through as a dict, users have the option to
send all configuration in via a YAML file. This is useful in situations where code changes are not desirable.

To use a YAML file, you must pass it in the `run` method of a pipeline instance:

```python
@step
def my_step() -> None:
  print("my step")

@pipeline
def my_pipeline(step1):
  step1()

pipeline_instance = my_pipeline(
  step1 =  my_step()
)

# Pass in a config file
pipeline_instance.run(config_path='/local/path/to/config.yaml')
```

The format of a YAML config file is exactly the same as the dict you would pass in python in the above two sections. The step specific settings are nested in a key called `steps`. Here is rough skeleton of a valid YAML config. All keys are optional.

```yaml
enable_cache: True
extra:
  tags: production
run_name: my_run
schedule: {}
settings: {}  # same as pipeline settings
steps:
  name_of_step_1:
    settings: {}  # same as step settings
  name_of_step_2:
    settings: {}
  ...
```

ZenML provides a convenient method that takes a pipeline instance and generates a config template based on its settings automatically:

```python
pipeline_instance.write_run_configuration_template(path='/local/path/to/config.yaml')
```

This will write a template file at `/local/path/to/config.yaml` with a commented out YAML file
with all possible options that the pipeline instance can take.

Here is an example of a YAML config file generated from the above method:

<details>

<summary>An example of a YAML config</summary>

Some configuration is commented out as it is not needed.

```yaml
enable_cache: True
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
  # get_first_num:
      enable_cache: false
      experiment_tracker: mlflow_tracker
    # extra: Mapping[str, Any]
    # outputs:
    #   first_num:
    #     artifact_source: Optional[str]
    #     materializer_source: Optional[str]
    # parameters: {}
    # settings:
    #   resources:
    #     cpu_count: Optional[PositiveFloat]
    #     gpu_count: Optional[PositiveInt]
    #     memory: Optional[ConstrainedStrValue]
    # step_operator: Optional[str]
  # get_random_int:
  #   enable_cache: Optional[bool]
  #   experiment_tracker: Optional[str]
  #   extra: Mapping[str, Any]
  #   outputs:
  #     random_num:
  #       artifact_source: Optional[str]
  #       materializer_source: Optional[str]
  #   parameters: {}
  #   settings:
  #     resources:
  #       cpu_count: Optional[PositiveFloat]
  #       gpu_count: Optional[PositiveInt]
  #       memory: Optional[ConstrainedStrValue]
  #   step_operator: Optional[str]
  # subtract_numbers:
  #   enable_cache: Optional[bool]
  #   experiment_tracker: Optional[str]
  #   extra: Mapping[str, Any]
  #   outputs:
  #     result:
  #       artifact_source: Optional[str]
  #       materializer_source: Optional[str]
  #   parameters: {}
  #   settings:
  #     resources:
  #       cpu_count: Optional[PositiveFloat]
  #       gpu_count: Optional[PositiveInt]
  #       memory: Optional[ConstrainedStrValue]
  #   step_operator: Optional[str]

```

</details>

### The `extra` dict

You might have noticed another dict that is available to pass through to steps and pipelines called `extra`. This dict is meant to be used to pass
any configuration down to the pipeline, step, or stack components that the user has use of.

An example of this is if I want to tag a pipeline, I can do the following:

```python
@pipeline(name='my_pipeline', extra={'tag': 'production'})
  ...
```

This tag is now associated and tracked with all pipeline runs, and can be fetched later with the [post-execution workflow](../../starter-guide/pipelines/fetching-pipelines.md):

```python
from zenml.post_execution import get_pipeline

p = get_pipeline('my_pipeline')

# print out the extra
print(p.runs[0].pipeline_configuration['extra'])
# {'tag': 'production'}
```

### Hierarchy and precedence

Some settings can be configured on pipelines and steps, some only on one of the two. Pipeline level settings will be automatically applied to all steps, but if the same setting is configured on a step as well that takes precedence. The next section explains in more detail how the step level settings
will be merged with pipeline settings.

### Merging settings on class/instance/run:

When a settings object is configured, ZenML merges the values with previously configured keys. E.g.:

```python
from zenml.config import ResourceSettings

@step(settings={"resources": ResourceSettings(cpu_count=2, memory="1GB")})
def my_step() -> None:
  ...

step_instance = my_step()
step_instance.configure(settings={"resources": ResourceSettings(gpu_count=1, memory="2GB")})
step_instance.configuration.settings["resources"] # cpu_count: 2, gpu_count=1, memory="2GB"
```

In the above example, the two settings were automatically merged.
