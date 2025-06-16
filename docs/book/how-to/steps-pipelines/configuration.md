---
description: Configuring and customizing your pipeline runs.
---

ZenML provides several approaches to configure your pipelines and steps:

### Understanding `.configure()` vs `.with_options()`

ZenML provides two primary methods to configure pipelines and steps: `.configure()` and `.with_options()`. While they accept the same parameters, they behave differently:

- **`.configure()`**: Modifies the configuration **in-place** and returns the same object.
- **`.with_options()`**: Creates a **new copy** with the applied configuration, leaving the original unchanged.

When to use each:
- Use `.with_options()` in most cases, especially inside pipeline definitions:
  ```python
  @pipeline
  def my_pipeline():
      # This creates a new configuration just for this instance
      my_step.with_options(parameters={"param": "value"})()
  ```
- Use `.configure()` only when you intentionally want to modify a step globally, and are aware that the change will affect all subsequent uses of that step.

## Approaches to Configuration

### Pipeline Configuration with `configure`

You can configure various aspects of a pipeline using the `configure` method:

```python
from zenml import pipeline

# Assuming MyPipeline is your pipeline function
# @pipeline
# def MyPipeline():
#     ...

# Create a pipeline
my_pipeline = MyPipeline()

# Configure the pipeline
my_pipeline.configure(
    enable_cache=False,
    enable_artifact_metadata=True,
    settings={
        "docker": {
            "parent_image": "zenml-io/zenml-cuda:latest"
        }
    }
)

# Run the pipeline
my_pipeline()
```

### Runtime Configuration with `with_options`

You can configure a pipeline at runtime using the `with_options` method:

```python
# Configure specific step parameters
my_pipeline.with_options(steps={"trainer": {"parameters": {"learning_rate": 0.01}}})()

# Or using a YAML configuration file
my_pipeline.with_options(config_file="path_to_yaml_file")()
```

### Step-Level Configuration

You can configure individual steps with the `@step` decorator:

```python
import tensorflow as tf
from zenml import step

@step(
    settings={
        # Custom materializer for handling output serialization
        "output_materializers": {
            "output": "zenml.materializers.tensorflow_materializer.TensorflowModelMaterializer"
        },
        # Step-specific experiment tracker settings
        "experiment_tracker.mlflow": {
            "experiment_name": "custom_experiment"
        }
    }
)
def train_model() -> tf.keras.Model:
    model = build_and_train_model()
    return model
```

### Direct Component Assignment

You can directly specify which stack components a step should use. This feature is only available for experiment trackers and stack components:

```python
from zenml import step

@step(experiment_tracker="mlflow_tracker", step_operator="vertex_ai")
def train_model():
    # This step will use MLflow for tracking and run on Vertex AI
    ...

@step(experiment_tracker="wandb", step_operator="kubernetes")
def evaluate_model():
    # This step will use Weights & Biases for tracking and run on Kubernetes
    ...
```

This direct specification is a concise way to assign different stack components to different steps. You can combine this with settings to configure the specific behavior of those components:

```python
from zenml import step

@step(step_operator="nameofstepoperator", settings={"step_operator": {"estimator_args": {"instance_type": "m7g.medium"}}})
def my_step():
    # This step will use the specified step operator with custom instance type
    ...

# Alternatively, using the appropriate settings class:
@step(step_operator="nameofstepoperator", settings={"step_operator": SagemakerStepOperatorSettings(instance_type="m7g.medium")})
def my_step():
    # Same configuration using the settings class
    ...
```

This approach allows you to use different components for different steps in your pipeline while also customizing their runtime behavior.

## Types of Settings

Settings in ZenML are categorized into two main types:

* **General settings** that can be used on all ZenML pipelines:
  * `DockerSettings` for container configuration
  * `ResourceSettings` for CPU, memory, and GPU allocation

* **Stack-component-specific settings** for configuring behaviors of components in your stack:
  * These use the pattern `<COMPONENT_CATEGORY>` or `<COMPONENT_CATEGORY>.<COMPONENT_FLAVOR>` as keys
  * Examples include `experiment_tracker.mlflow` or just `step_operator`

## Configuration Hierarchy

There are a few general rules when it comes to settings and configurations that are applied in multiple places. Generally the following is true:

* Configurations in code override configurations made inside of the yaml file
* Configurations at the step level override those made at the pipeline level
* In case of attributes the dictionaries are merged

```python
from zenml import pipeline, step
from zenml.config import ResourceSettings


@step
def load_data(parameter: int) -> dict:
    ...

@step(settings={"resources": ResourceSettings(gpu_count=1, memory="2GB")})
def train_model(data: dict) -> None:
    ...


@pipeline(settings={"resources": ResourceSettings(cpu_count=2, memory="1GB")}) 
def simple_ml_pipeline(parameter: int):
    ...
    
# ZenMl merges the two configurations and uses the step configuration to override 
# values defined on the pipeline level

train_model.configuration.settings["resources"]
# -> cpu_count: 2, gpu_count=1, memory="2GB"

simple_ml_pipeline.configuration.settings["resources"]
# -> cpu_count: 2, memory="1GB"
```

## Common Setting Types

### Resource Settings

Resource settings allow you to specify the CPU, memory, and GPU requirements for your steps:

```python
from zenml.config import ResourceSettings

@step(settings={"resources": ResourceSettings(gpu_count=1, memory="2GB")})
def train_model(data: dict) -> None:
    ...

@pipeline(settings={"resources": ResourceSettings(cpu_count=2, memory="1GB")}) 
def simple_ml_pipeline(parameter: int):
    ...
```

When both pipeline and step resource settings are specified, they are merged with step settings taking precedence:

```python
# Result of merging the above configurations:
# train_model.configuration.settings["resources"]
# -> cpu_count: 2, gpu_count=1, memory="2GB"
```

{% hint style="info" %}
Note that `ResourceSettings` are not always applied by all orchestrators. The ability to enforce resource constraints depends on the specific orchestrator being used. Some orchestrators like Kubernetes fully support these settings, while others may ignore them. In order to learn more, read the [individual pages](https://docs.zenml.io/stacks/stack-components/orchestrators) of the orchestrator you are using.
{% endhint %}

### Docker Settings

Docker settings allow you to customize the containerization process:

```python
@pipeline(settings={
    "docker": {
        "parent_image": "zenml-io/zenml-cuda:latest"
    }
})
def my_pipeline():
    ...
```

For more detailed information on containerization options, see the [containerization guide](../containerization/containerization.md).

## Stack Component Configuration

### Registration-time vs Runtime Stack Component Settings

Stack components have two types of configuration:

1. **Registration-time configuration**: Static settings defined when registering a component
   ```bash
   # Example: Setting a fixed tracking URL for MLflow
   zenml experiment-tracker register mlflow_tracker --flavor=mlflow --tracking_url=http://localhost:5000
   ```

2. **Runtime settings**: Dynamic settings that can change between pipeline runs
   ```python
   # Example: Setting experiment name that changes for each run
   @step(settings={"experiment_tracker.mlflow": {"experiment_name": "custom_experiment"}})
   def my_step():
       ...
   ```

Even for runtime settings, you can set default values during registration:
```bash
# Setting a default value for "nested" setting
zenml experiment-tracker register <n> --flavor=mlflow --nested=True
```

### Using the Right Key for Stack Component Settings

When specifying stack-component-specific settings, the key follows this pattern:

```python
# Using just the component category
@step(settings={"step_operator": {"estimator_args": {"instance_type": "m7g.medium"}}})

# Or using the component category and flavor
@step(settings={"experiment_tracker.mlflow": {"experiment_name": "custom_experiment"}})
```

If you specify just the category (e.g., `step_operator`), ZenML applies these settings to whatever flavor of component is in your stack. If the settings don't apply to that flavor, they are ignored.

## Making Configurations Flexible with Environment Variables

You can make your configurations more flexible by referencing environment variables using the placeholder syntax `${ENV_VARIABLE_NAME}`:

**In code:**

```python
from zenml import step

@step(extra={"value_from_environment": "${ENV_VAR}"})
def my_step() -> None:
    ...
```

**In configuration files:**

```yaml
extra:
  value_from_environment: ${ENV_VAR}
  combined_value: prefix_${ENV_VAR}_suffix
```

This allows you to easily adapt your pipelines to different environments without changing code.

## Advanced Pipeline Triggering

For triggering pipelines from a client or another pipeline, you can use a `PipelineRunConfiguration` object. This approach is covered in the [advanced template usage documentation](https://docs.zenml.io/how-to/trigger-pipelines/use-templates-python#advanced-usage-run-a-template-from-another-pipeline).

## Autogenerate a template yaml file

If you want to generate a template yaml file of your specific pipeline, you can do so by using the `.write_run_configuration_template()` method. This will generate a yaml file with all options commented out. This way you can pick and choose the settings that are relevant to you.

```python
from zenml import pipeline
...

@pipeline(enable_cache=True) # set cache behavior at step level
def simple_ml_pipeline(parameter: int):
    dataset = load_data(parameter=parameter)
    train_model(dataset)

simple_ml_pipeline.write_run_configuration_template(path="<Insert_path_here>")
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
    required_integrations: List[str]
    requirements: Union[NoneType, str, List[str]]
    skip_build: bool
    prevent_build_reuse: bool
    allow_including_files_in_images: bool
    allow_download_from_code_repository: bool
    allow_download_from_artifact_store: bool
    target_repository: str
    user: Optional[str]
  resources:
    cpu_count: Optional[PositiveFloat]
    gpu_count: Optional[NonNegativeInt]
    memory: Optional[ConstrainedStrValue]
steps:
  load_data:
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
        python_package_installer: PythonPackageInstaller
        replicate_local_python_environment: Union[List[str], PythonEnvironmentExportMethod,
         NoneType]
        required_integrations: List[str]
        requirements: Union[NoneType, str, List[str]]
        skip_build: bool
        prevent_build_reuse: bool
        allow_including_files_in_images: bool
        allow_download_from_code_repository: bool
        allow_download_from_artifact_store: bool
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
        required_integrations: List[str]
        requirements: Union[NoneType, str, List[str]]
        skip_build: bool
        prevent_build_reuse: bool
        allow_including_files_in_images: bool
        allow_download_from_code_repository: bool
        allow_download_from_artifact_store: bool
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

{% hint style="info" %}
When you want to configure your pipeline with a certain stack in mind, you can do so as well: `...write_run_configuration_template(stack=<Insert_stack_here>)`
{% endhint %}