---
description: Configuring and customizing your pipeline runs.
---

ZenML provides several approaches to configure your pipelines and steps:

### Understanding `.configure()` vs `.with_options()`

ZenML provides two primary methods to configure pipelines and steps: `.configure()` and `.with_options()`. While they accept the same parameters, they behave differently:

- **`.configure()`**: Modifies the configuration **in-place** and returns the same object.
- **`.with_options()`**: Creates a **new copy** with the applied configuration, leaving the original unchanged.

When to use each:
- Use `.with_options()` when you need to create multiple variants of a step/pipeline, especially for running a step with different parameters.
- Use `.configure()` when applying a general configuration you'll only use once.

### Pipeline Configuration with `configure`

You can configure various aspects of a pipeline using the `configure` method:

```python
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

You can directly specify which stack components a step should use:

```python
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

## Runtime Configuration of Pipelines

You can configure a pipeline at runtime using the `with_options` method:

```python
# Configure specific step parameters
my_pipeline.with_options(steps={"trainer": {"parameters": {"learning_rate": 0.01}}})()

# Or using a YAML configuration file
my_pipeline.with_options(config_file="path_to_yaml_file")()
```

For triggering pipelines from a client or another pipeline, you can use a `PipelineRunConfiguration` object. This approach is covered in the [advanced template usage documentation](https://docs.zenml.io/how-to/trigger-pipelines/use-templates-python#advanced-usage-run-a-template-from-another-pipeline).


