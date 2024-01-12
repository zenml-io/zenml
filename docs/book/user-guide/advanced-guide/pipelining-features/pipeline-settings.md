---
description: Using settings to configure runtime configuration.
---

# Controlling settings of your pipeline

## Settings in ZenML

Settings in ZenML allow you to configure runtime configurations for stack components and pipelines. Concretely, they allow you to configure:

* The [resources](../infrastructure-management/scale-compute-to-the-cloud.md#specify-resource-requirements-for-steps) required for a step
* Configuring the [containerization](../infrastructure-management/containerize-your-pipeline.md) process of a pipeline (e.g. What requirements get installed in the Docker image)
* Stack component-specific configuration, e.g., if you have an experiment tracker passing in the name of the experiment at runtime

You will learn about all of the above in more detail later, but for now, let's try to understand that all of this configuration flows through one central concept, called `BaseSettings` (From here on, we use `settings` and `BaseSettings` as analogous in this guide).

### Types of settings

Settings are categorized into two types:

* **General settings** that can be used on all ZenML pipelines. Examples of these are:
  * [`DockerSettings`](../infrastructure-management/containerize-your-pipeline.md) to specify docker settings.
  * [`ResourceSettings`](../infrastructure-management/scale-compute-to-the-cloud.md#specify-resource-requirements-for-steps) to specify resource settings.
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
