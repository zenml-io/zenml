---
description: Understanding how to configure a ZenML pipeline
---

# Configuring a step and a pipeline

The configuration of a step and/or a pipeline determines various details of how a run is executed. It is an important aspect of running workloads in production, and as such deserves a dedicated section in these docs.

We have already learned about some basics of [configuration in the production guide](../../production-guide/configure-pipeline.md). Here we go into more depth.

## How to apply configuration

Before we learn about all the different configuration options, let's briefly look at *how* configuration can be applied to a step or a pipeline. We start with the simplest configuration, a boolean flag called `enable_cache`, that specifies whether caching should be enabled or disabled. There are essentially three ways you could configure this:

### Method 1: Directly on the decorator

The most basic way to configure a step or a pipeline `@step` and `@pipeline` decorators:

```python
@step(enable_cache=...)
...

@pipeline(enable_cache=...)
...
```

{% hint style="info" %}
Once you set configuration on a pipeline, they will be applied to all steps with some exceptions. See the [section on precedence for more details](configure-steps-pipelines.md#hierarchy-and-precedence).
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

As all configuration can be passed through as a dictionary, users have the option to send all configurations in via a YAML file. This is useful in situations where code changes are not desirable.

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

The YAML method is the recommended method for applying configuration in production. It has the benefit of being declarative and decoupled from the codebase.

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

The method `write_run_configuration_template` generates a config template (at path `run.yaml` in this case) that includes all configuration options for this specific pipeline and your active stack. Let's run the pipeline:

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
model:
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
    model:
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
    model:
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

The generated config contains most of the available configuration options for this pipeline. Let's walk through it section by section: 

### `enable_XXX` parameters

These are boolean flags for various configurations:

* `enable_artifact_metadata`: Whether to [associate metadata with artifacts or not](../data-management/handle-custom-data-types.md#optional-which-metadata-to-extract-for-the-artifact).
* `enable_artifact_visualization`: Whether to [attach visualizations of artifacts](../data-management/visualize-artifacts.md).
* `enable_cache`: Utilize [caching](../../starter-guide/cache-previous-executions.md) or not.
* `enable_step_logs`: Enable tracking [step logs](managing-steps.md#enable-or-disable-logs-storing).

### `build` ID

The UUID of the [`build`](../infrastructure-management/containerize-your-pipeline.md) to use for this pipeline. If specified, Docker image building is skipped for remote orchestrators, and the Docker image specified in this build is used.

### `extra` dict

This is a dictionary that is available to be passed to steps and pipelines called `extra`. This dictionary is meant to be used to pass any configuration down to the pipeline, step, or stack components that the user has use of. See an example in [this section](#fetching-configuration).

### Configuring the `model`

Specifies the ZenML [Model](../../starter-guide/track-ml-models.md) to use for this pipeline.

### Pipeline and step `parameters`

A dictionary of JSON-serializable [parameters](managing-steps.md#parameters-for-your-steps) specified at the pipeline or step level. For example:

```yaml
parameters:
    gamma: 0.01

steps:
    trainer:
        parameters:
            gamma: 0.001
```

Corresponds to:

```python
@step
def trainer(gamma: float):
    # Use gamma as normal
    print(gamma)

@pipeline
def my_pipeline(gamma: float)
    # use gamma or pass it into the step
    print(0.01)
    trainer(gamma=gamma)
```

Important note, in the above case, the value of the step would be the one defined in the `steps` key (i.e. 0.001). So the YAML config always takes precedence over pipeline parameters that are passed down to steps in code. Read [this section for more details](#hierarchy-and-precedence).

Normally, parameters defined at the pipeline level are used in multiple steps, and then no step-level configuration is defined.

{% hint style="info" %}
Note that `parameters` are different from `artifacts`. Parameters are JSON-serializable values that are passed in the runtime configuration of a pipeline. Artifacts are inputs and outputs of a step, and need not always be JSON-serializable ([materializers](../data-management/handle-custom-data-types.md) handle their persistence in the [artifact store](../../../stacks-and-components/component-guide/artifact-stores/artifact-stores.md)).
{% endhint %}

### Setting the `run_name`

To change the name for a run, pass `run_name` as a parameter. This can be a dynamic value as well. Read [here for details.](../../starter-guide/create-an-ml-pipeline.md).

### Real-time `settings`

Settings are special runtime configurations of a pipeline or a step that require a [dedicated section](pipeline-settings.md). In short, they define a whole bunch of execution configuration such as Docker building and resource settings.

### `failure_hook_source` and `success_hook_source`

The `source` of the [failure and success hooks](../pipelining-features/use-failure-success-hooks.md).

### Step-specific configuration

A lot of pipeline-level configuration can also be applied at a step level (as we already seen with the `enable_cache` flag). However, there is some configuration that is step-specific, meaning it cannot be applied at a pipeline level, but only at a step level.

* `experiment_tracker`: Name of the [experiment_tracker](../../../stacks-and-components/component-guide/experiment-trackers/experiment-trackers.md) to enable for this step. This experiment_tracker should be defined in the active stack with the same name. 
* `step_operator`: Name of the [step_operator](../../../stacks-and-components/component-guide/step-operators/step-operators.md) to enable for this step. This step_operator should be defined in the active stack with the same name. 
* `outputs`: This is configuration of the output artifacts of this step. This is further keyed by output name (by default, step outputs [are named `output`](managing-steps.md#step-output-names)). The most interesting configuration here is the `materializer_source`, which is the UDF path of the materializer in code to use for this output (e.g. `materializers.some_data.materializer.materializer_class`). Read more about this source path [here](../data-management/handle-custom-data-types.md).

Learn more about step configuration in the [dedicated section on managing steps](managing-steps.md).

## Hierarchy and precedence

Some things can be configured on pipelines and steps, some only on one of the two. Pipeline-level settings will be automatically applied to all steps, but if the same setting is configured on a step as well that takes precedence. 

When an object is configured, ZenML merges the values with previously-configured keys. E.g.:

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

In the above example, the two settings configurations were automatically merged.


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
