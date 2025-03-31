---
description: >-
  Learn how to configure ZenML pipelines using YAML configuration files and runtime settings.
---

# Configuration & Settings

ZenML provides powerful configuration capabilities that allow you to customize pipeline and step behavior without changing your code. This is particularly useful for:

- Separating configuration from code
- Experimenting with different parameters
- Managing environment-specific settings (dev/prod)
- Setting up consistent configurations across a team

## Configuration with YAML Files

You can configure pipelines and steps using YAML files, which can be specified when running a pipeline:

```python
my_pipeline.with_options(config_path="config.yaml")()
```

### Sample Configuration File

Here's an example of a configuration file with common settings:

```yaml
# Enable flags
enable_artifact_metadata: True
enable_artifact_visualization: False
enable_cache: False
enable_step_logs: True

# Pipeline parameters
parameters: 
  dataset_name: "my_dataset"
  learning_rate: 0.01

# Run name
run_name: "my_experiment_run"

# Step-specific configuration
steps:
  train_model:
    parameters:
      learning_rate: 0.001
    enable_cache: True
    
    # Step-specific components
    experiment_tracker: "mlflow_tracker"
```

## What Can Be Configured

### Pipeline and Step Parameters

You can specify parameters for pipelines and steps:

```yaml
# Pipeline parameters
parameters:
  dataset_name: "my_dataset"
  learning_rate: 0.01

# Step parameters
steps:
  my_step:
    parameters:
      learning_rate: 0.001
```

This corresponds to:

```python
@step
def my_step(learning_rate: float):
    # Use learning_rate parameter
    pass

@pipeline
def my_pipeline(dataset_name: str, learning_rate: float):
    # Use pipeline parameters
    my_step(learning_rate=learning_rate)
```

### Enable Flags

These boolean flags control various aspects of pipeline execution:

```yaml
enable_artifact_metadata: True     # Whether to associate metadata with artifacts
enable_artifact_visualization: True # Whether to attach visualizations of artifacts
enable_cache: True                 # Whether to use caching
enable_step_logs: True             # Whether to track step logs
```

You can set these at both pipeline and step levels.

### Docker Settings

Configure Docker container settings for pipeline execution:

```yaml
settings:
  docker:
    apt_packages: ["curl", "git"]
    copy_files: True
    dockerfile: "Dockerfile"
    dockerignore: ".dockerignore"
    environment:
      ZENML_LOGGING_VERBOSITY: DEBUG
    parent_image: "zenml-io/zenml-cuda"
    requirements: ["torch", "numpy"]
    skip_build: False
```

### Resource Settings

Configure compute resources for pipeline or step execution:

```yaml
settings:
  resources:
    cpu_count: 2
    gpu_count: 1
    memory: "4Gb"
```

### Stack Component Settings

Configure specific stack components for steps:

```yaml
steps:
  train_model:
    experiment_tracker: "mlflow_tracker"
    step_operator: "vertex_gpu"
    
    # Component-specific settings
    settings:
      step_operator.sagemaker:
        estimator_args:
          instance_type: m7g.medium
```

### Model Configuration

Link a pipeline to a ZenML Model:

```yaml
model:
  name: "classification_model"
  version: "production"
  description: "Classifier for image data"
  tags: ["sklearn", "classification"]
```

### Run Name

Set a custom name for the pipeline run:

```yaml
run_name: "training_run_20230601"
```

### Scheduling

Configure pipeline scheduling (if supported by the orchestrator):

```yaml
schedule:
  catchup: true
  cron_expression: "0 0 * * *"  # Daily at midnight
```

## Configuration Hierarchy

ZenML follows a specific hierarchy when resolving configuration:

1. **Runtime Python code** - Highest precedence
2. **Step-level YAML configuration**
3. **Pipeline-level YAML configuration**
4. **Default values**

For example, if you set a parameter in code and also in the YAML configuration file, the value in the code will take precedence.

## Autogenerating Template YAML Files

ZenML provides a command to generate a template configuration file for a pipeline:

```bash
zenml pipeline build-configuration my_pipeline > config.yaml
```

This generates a YAML file with all possible configuration options for your pipeline.

## Environment Variables in Configuration

You can reference environment variables in your YAML configuration:

```yaml
settings:
  docker:
    environment:
      API_KEY: ${MY_API_KEY}
```

This will use the value of the `MY_API_KEY` environment variable at runtime.

## Using Configuration Files for Different Environments

A common pattern is to maintain different configuration files for different environments:

```
├── configs/
│   ├── dev.yaml     # Development configuration
│   ├── staging.yaml # Staging configuration
│   └── prod.yaml    # Production configuration
```

You can then specify which configuration to use:

```python
# For development
my_pipeline.with_options(config_path="configs/dev.yaml")()

# For production
my_pipeline.with_options(config_path="configs/prod.yaml")()
```

## Finding Which Configuration Was Used for a Run

To determine which configuration was used for a specific run:

```python
from zenml.client import Client

run = Client().get_pipeline_run("<RUN_ID>")
config = run.config
```

This allows you to reproduce the exact configuration used for a specific run.

## Conclusion

Configuration and settings in ZenML provide a powerful way to customize pipeline behavior without changing your code. By leveraging YAML configuration files, you can separate configuration from implementation, making your ML workflows more flexible and maintainable.

See also:
- [Steps & Pipelines](./steps_and_pipelines.md) - Core building blocks
- [Execution Parameters](./execution_parameters.md) - Runtime parameters
- [Logging](./logging.md) - Logging configuration 