# What can be configured

## Sample YAML file

Here is an example of a sample YAML file, with the most important configuration highlighted. For brevity,
we have removed all possible keys. To view a sample file with all possible keys, refer to
[this page](./autogenerate-a-template-yaml-file.md).

```yaml
build: dcd6fafb-c200-4e85-8328-428bef98d804

enable_artifact_metadata: True
enable_artifact_visualization: False
enable_cache: False
enable_step_logs: True

extra: 
  any_param: 1
  another_random_key: "some_string"

model:
  name: str
  version: Union[ModelStages, int, str, NoneType]

  audience: Optional[str]
  description: Optional[str]
  ethics: Optional[str]
  license: Optional[str]
  limitations: Optional[str]
  tags: Optional[List[str]]
  trade_offs: Optional[str]
  use_cases: Optional[str]

parameters: Optional[Mapping[str, Any]]
run_name: Optional[str]

schedule:
  catchup: bool
  cron_expression: Optional[str]
  end_time: Optional[datetime]
  interval_second: Optional[timedelta]
  name: Optional[str]
  run_once_start_time: Optional[datetime]
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
    python_package_installer: PythonPackageInstaller
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
  train_model:
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
    outputs: {}
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
        python_package_installer: PythonPackageInstaller
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

## Deep-dive

### `enable_XXX` parameters

These are boolean flags for various configurations:

* `enable_artifact_metadata`: Whether to [associate metadata with artifacts or not](../handle-data-artifacts/handle-custom-data-types.md#optional-which-metadata-to-extract-for-the-artifact).
* `enable_artifact_visualization`: Whether to [attach visualizations of artifacts](../handle-data-artifacts/visualize-artifacts.md).
* `enable_cache`: Utilize [caching](../overview/control-caching-behavior.md) or not.
* `enable_step_logs`: Enable tracking [step logs](../control-logging/enable-or-disable-logs-storing.md).

```yaml
enable_artifact_metadata: True
enable_artifact_visualization: True
enable_cache: True
enable_step_logs: True
```

### `build` ID

The UUID of the [`build`](../customize-docker-builds/) to use for this pipeline. If specified, Docker image building is skipped for remote orchestrators, and the Docker image specified in this build is used.

```yaml
build: <INSERT-BUILD-ID-HERE>
```

### Configuring the `model`

Specifies the ZenML [Model](../../user-guide/starter-guide/track-ml-models.md) to use for this pipeline.

```yaml
model:
  name: "ModelName"
  version: "production"
  description: An example model
  tags: ["classifier"]
```

### Pipeline and step `parameters`

A dictionary of JSON-serializable [parameters](./) specified at the pipeline or step level. For example:

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
from zenml import step, pipeline

@step
def trainer(gamma: float):
    # Use gamma as normal
    print(gamma)

@pipeline
def my_pipeline(gamma: float):
    # use gamma or pass it into the step
    print(0.01)
    trainer(gamma=gamma)
```

Important note, in the above case, the value of the step would be the one defined in the `steps` key (i.e. 0.001). So the YAML config always takes precedence over pipeline parameters that are passed down to steps in code. Read [this section for more details](configuration-hierarchy.md).

Normally, parameters defined at the pipeline level are used in multiple steps, and then no step-level configuration is defined.

{% hint style="info" %}
Note that `parameters` are different from `artifacts`. Parameters are JSON-serializable values that are passed in the runtime configuration of a pipeline. Artifacts are inputs and outputs of a step, and need not always be JSON-serializable ([materializers](../handle-data-artifacts/handle-custom-data-types.md) handle their persistence in the [artifact store](https://github.com/zenml-io/zenml/blob/feature/gro-1047-docs/docs/book/how-to/configure-stack-components/artifact-stores/README.md)).
{% endhint %}

### Setting the `run_name`

To change the name for a run, pass `run_name` as a parameter. This can be a dynamic value as well.&#x20;

```python
run_name: <INSERT_RUN_NAME_HERE>  
```

{% hint style="warning" %}
You will not be able to run with the same run\_name twice. Do not set this statically when running on a schedule. Try to include some auto-incrementation or timestamp to the name.
{% endhint %}

### Stack Component Runtime settings

{% hint style="info" %}
Settings are special runtime configurations of a pipeline or a step that require a [dedicated section](runtime-configuration.md). In short, they define a bunch of execution configuration such as Docker building and resource settings.
{% endhint %}

### Docker Settings

Docker Settings can be passed in directly as objects, or a dictionary representation of the object. For example, the Docker configuration can be set in configuration files as follows:

```yaml
settings:
  docker:
    requirements:
      - pandas
    
```

{% hint style="info" %}
Find a complete list of all Docker Settings [here](https://sdkdocs.zenml.io/latest/core\_code\_docs/core-config/#zenml.config.docker\_settings.DockerSettings). To learn more about pipeline containerization consult our documentation on this [here](../customize-docker-builds/).
{% endhint %}

### Resource Settings

### `failure_hook_source` and `success_hook_source`

The `source` of the [failure and success hooks](../overview/use-failure-success-hooks.md) can be specified.

### Step-specific configuration

A lot of pipeline-level configuration can also be applied at a step level (as we have already seen with the `enable_cache` flag). However, there is some configuration that is step-specific, meaning it cannot be applied at a pipeline level, but only at a step level.

* `experiment_tracker`: Name of the [experiment\_tracker](https://github.com/zenml-io/zenml/blob/feature/gro-1047-docs/docs/book/how-to/configure-stack-components/experiment-trackers/README.md) to enable for this step. This experiment\_tracker should be defined in the active stack with the same name.
* `step_operator`: Name of the [step\_operator](https://github.com/zenml-io/zenml/blob/feature/gro-1047-docs/docs/book/how-to/configure-stack-components/step-operators/README.md) to enable for this step. This step\_operator should be defined in the active stack with the same name.
* `outputs`: This is configuration of the output artifacts of this step. This is further keyed by output name (by default, step outputs [are named `output`](../handle-data-artifacts/return-multiple-outputs-from-a-step.md)). The most interesting configuration here is the `materializer_source`, which is the UDF path of the materializer in code to use for this output (e.g. `materializers.some_data.materializer.materializer_class`). Read more about this source path [here](../handle-data-artifacts/handle-custom-data-types.md).

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
