---
description: >-
  Learn how to configure ZenML pipelines using YAML configuration files.
---

# Configuration with YAML

ZenML provides powerful configuration capabilities through YAML files that allow you to customize pipeline and step behavior without changing your code. This is particularly useful for:

- Separating configuration from code
- Experimenting with different parameters across multiple pipeline runs
- Managing environment-specific settings (development, staging, production)
- Setting up consistent configurations across a team of data scientists
- Enabling reproducibility by storing configuration alongside run history

## Using YAML Configuration Files

You can apply a YAML configuration file when running a pipeline:

```python
my_pipeline.with_options(config_path="config.yaml")()
```

This approach allows you to change pipeline behavior without modifying your code, making it easier to manage different configurations and reproduce past runs.

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
      learning_rate: 0.001  # Override the pipeline parameter for this step
    enable_cache: True      # Override the pipeline cache setting
    
    # Step-specific components
    experiment_tracker: "mlflow_tracker"
```

When this configuration is applied, ZenML will:
1. Configure the overall pipeline with the top-level settings
2. Apply step-specific overrides for the `train_model` step
3. Use these settings during pipeline execution

## What Can Be Configured in YAML

### Pipeline and Step Parameters

You can specify parameters for pipelines and steps:

```yaml
# Pipeline parameters
parameters:
  dataset_name: "my_dataset"
  learning_rate: 0.01
  batch_size: 32
  epochs: 10

# Step parameters
steps:
  preprocessing:
    parameters:
      normalize: True
      fill_missing: "mean"
  
  train_model:
    parameters:
      learning_rate: 0.001  # Override the pipeline parameter
      optimizer: "adam"
```

### Enable Flags

These boolean flags control various aspects of pipeline execution and logging:

```yaml
# Pipeline-level flags
enable_artifact_metadata: True     # Whether to collect and store metadata for artifacts
enable_artifact_visualization: True # Whether to generate visualizations for artifacts
enable_cache: True                 # Whether to use caching for steps
enable_step_logs: True             # Whether to capture and store step logs

# Step-specific flags
steps:
  preprocessing:
    enable_cache: False            # Disable caching for this step only
  train_model:
    enable_artifact_visualization: False  # Disable visualizations for this step
```

These flags are particularly useful for:
- **Development**: Enable detailed logs and visualizations during development
- **Production**: Disable expensive operations like visualizations in production
- **Debugging**: Disable caching when troubleshooting to ensure fresh execution

### Docker Settings

Configure Docker container settings for pipeline execution:

```yaml
settings:
  docker:
    # Packages to install via apt-get
    apt_packages: ["curl", "git", "libgomp1"]
    
    # Whether to copy files from current directory to the Docker image
    copy_files: True
    
    # Custom Dockerfile and .dockerignore to use
    dockerfile: "custom/Dockerfile"
    dockerignore: ".dockerignore"
    
    # Environment variables to set in the container
    environment:
      ZENML_LOGGING_VERBOSITY: DEBUG
      PYTHONUNBUFFERED: "1"
      DATA_DIR: "/data"
    
    # Parent image to use for building
    parent_image: "zenml-io/zenml-cuda:latest"
    
    # Additional Python packages to install
    requirements: ["torch==1.10.0", "transformers>=4.0.0", "pandas"]
    
    # Skip Docker build (use existing image)
    skip_build: False
```

### Resource Settings

Configure compute resources for pipeline or step execution:

```yaml
# Pipeline-level resource settings
settings:
  resources:
    cpu_count: 2
    gpu_count: 1
    memory: "4Gb"
    accelerator_type: "nvidia-tesla-t4"

# Step-specific resource settings
steps:
  train_model:
    settings:
      resources:
        cpu_count: 4
        gpu_count: 2
        memory: "16Gb"
```

### Stack Component Settings

Configure specific stack components for steps:

```yaml
steps:
  train_model:
    # Use specific named components
    experiment_tracker: "mlflow_tracker"
    step_operator: "vertex_gpu"
    
    # Component-specific settings
    settings:
      # AWS SageMaker specific configuration
      step_operator.sagemaker:
        estimator_args:
          instance_type: "ml.m5.xlarge"
          max_run: 86400
          
      # MLflow specific configuration
      experiment_tracker.mlflow:
        experiment_name: "image_classification"
        nested: True
```

### Model Configuration

Link a pipeline to a ZenML Model:

```yaml
model:
  name: "classification_model"
  version: "production"
  description: "Image classifier trained on the CIFAR-10 dataset"
  tags: ["computer-vision", "classification", "pytorch"]
  
  # Specific model version
  version: "1.2.3"
  
  # Link specific steps to this model
  steps:
    evaluate:
      model:
        name: "classification_model"  # Step-specific model link
```

### Run Name

Set a custom name for the pipeline run:

```yaml
run_name: "training_run_cifar10_resnet50_lr0.001"
```

### Scheduling

Configure pipeline scheduling when using an orchestrator that supports it:

```yaml
schedule:
  # Whether to run the pipeline for past dates if schedule is missed
  catchup: false
  
  # Cron expression for scheduling (daily at midnight)
  cron_expression: "0 0 * * *"
  
  # Time to start scheduling from
  start_time: "2023-06-01T00:00:00Z"
  
  # When to stop scheduling
  end_time: "2023-12-31T23:59:59Z"
```

## Configuration Hierarchy and Resolution

ZenML follows a specific hierarchy when resolving configuration:

1. **Runtime Python code** - Highest precedence
2. **Step-level YAML configuration**
   ```yaml
   steps:
     train_model:
       parameters:
         learning_rate: 0.001  # Overrides pipeline-level setting
   ```
3. **Pipeline-level YAML configuration**
   ```yaml
   parameters:
     learning_rate: 0.01  # Lower precedence than step-level
   ```
4. **Default values in code** - Lowest precedence

## Autogenerating Template YAML Files

ZenML provides a command to generate a template configuration file:

```bash
zenml pipeline build-configuration my_pipeline > config.yaml
```

This generates a YAML file with:
- All pipeline parameters with their default values
- All step parameters with their default values
- All possible configuration options (enable flags, settings, etc.)

## Environment Variables in Configuration

You can reference environment variables in your YAML configuration:

```yaml
settings:
  docker:
    environment:
      # References an environment variable from the host system
      API_KEY: ${MY_API_KEY}
      DATABASE_URL: ${DB_CONNECTION_STRING}
```

If an environment variable is not found, ZenML will raise an error during pipeline execution.

## Using Configuration Files for Different Environments

A common pattern is to maintain different configuration files for different environments:

```
├── configs/
│   ├── dev.yaml     # Development configuration
│   ├── staging.yaml # Staging configuration
│   └── prod.yaml    # Production configuration
```

Example development configuration:
```yaml
# dev.yaml
enable_cache: False
enable_step_logs: True
parameters:
  dataset_size: "small"
settings:
  docker:
    parent_image: "zenml-io/zenml:latest"
```

Example production configuration:
```yaml
# prod.yaml
enable_cache: True
enable_step_logs: False
parameters:
  dataset_size: "full"
settings:
  docker:
    parent_image: "zenml-io/zenml-cuda:latest"
  resources:
    cpu_count: 8
    memory: "16Gb"
```

You can then specify which configuration to use:

```python
# For development
my_pipeline.with_options(config_path="configs/dev.yaml")()

# For production
my_pipeline.with_options(config_path="configs/prod.yaml")()
```

## Finding Which Configuration Was Used for a Run

To access the configuration that was used for a specific run:

```python
from zenml.client import Client

# Get a specific pipeline run
run = Client().get_pipeline_run("<RUN_ID>")

# Access the configuration
config = run.config
```

## Conclusion

YAML configuration in ZenML provides a powerful way to customize pipeline behavior without changing your code. By leveraging configuration files, you can separate configuration from implementation, making your ML workflows more flexible, maintainable, and reproducible.

See also:
- [Steps & Pipelines](./steps_and_pipelines.md) - Core building blocks
- [Advanced Features](./advanced_features.md) - Advanced pipeline features 