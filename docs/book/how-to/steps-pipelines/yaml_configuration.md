---
description: >-
  Learn how to configure ZenML pipelines using YAML configuration files.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Configuration with YAML

ZenML provides configuration capabilities through YAML files that allow you to customize pipeline and step behavior without changing your code. This is particularly useful for separating configuration from code, experimenting with different parameters, and ensuring reproducibility.

## Basic Usage

You can apply a YAML configuration file when running a pipeline:

```python
my_pipeline.with_options(config_path="config.yaml")()
```

This allows you to change pipeline behavior without modifying your code.

### Sample Configuration File

Here's a simple example of a YAML configuration file:

```yaml
# Enable/disable features
enable_cache: False
enable_step_logs: True

# Pipeline parameters
parameters: 
  dataset_name: "my_dataset"
  learning_rate: 0.01

# Step-specific configuration
steps:
  train_model:
    parameters:
      learning_rate: 0.001  # Override the pipeline parameter for this step
    enable_cache: True      # Override the pipeline cache setting
```

### Configuration Hierarchy

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

This hierarchy allows you to define base configurations at the pipeline level and override them for specific steps as needed.

## Configuring Steps and Pipelines

### Pipeline and Step Parameters

You can specify parameters for pipelines and steps, similar to how you'd define them in Python code:

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

These settings correspond directly to the parameters you'd normally pass to your pipeline and step functions.

### Enable Flags

These boolean flags control aspects of pipeline execution that were covered in the Advanced Features section:

```yaml
# Pipeline-level flags
enable_artifact_metadata: True      # Whether to collect and store metadata for artifacts
enable_artifact_visualization: True  # Whether to generate visualizations for artifacts
enable_cache: True                  # Whether to use caching for steps
enable_step_logs: True              # Whether to capture and store step logs

# Step-specific flags
steps:
  preprocessing:
    enable_cache: False             # Disable caching for this step only
  train_model:
    enable_artifact_visualization: False  # Disable visualizations for this step
```

### Run Name

Set a custom name for the pipeline run:

```yaml
run_name: "training_run_cifar10_resnet50_lr0.001"
```

{% hint style="warning" %}
**Important:** Pipeline run names must be unique within a project. If you try to run a pipeline with a name that already exists, you'll get an error. To avoid this:

1. **Use dynamic placeholders** to ensure uniqueness:
   ```yaml
   # Example 1: Use placeholders for date and time to ensure uniqueness
   run_name: "training_run_{date}_{time}"
   
   # Example 2: Combine placeholders with specific details for better context
   run_name: "training_run_cifar10_resnet50_lr0.001_{date}_{time}"
   ```

2. **Remove the 'run_name' from your config** to let ZenML auto-generate unique names

3. **Change the run_name** before rerunning the pipeline

Available placeholders: `{date}`, `{time}`, and any parameters defined in your pipeline configuration.
{% endhint %}

## Resource and Component Configuration

### Docker Settings

Configure Docker container settings for pipeline execution:

```yaml
settings:
  docker:
    # Packages to install via apt-get
    apt_packages: ["curl", "git", "libgomp1"]
    
    # Whether to copy files from current directory to the Docker image
    copy_files: True
    
    # Environment variables to set in the container
    environment:
      ZENML_LOGGING_VERBOSITY: DEBUG
      PYTHONUNBUFFERED: "1"
    
    # Parent image to use for building
    parent_image: "zenml-io/zenml-cuda:latest"
    
    # Additional Python packages to install
    requirements: ["torch==1.10.0", "transformers>=4.0.0", "pandas"]
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
      # MLflow specific configuration
      experiment_tracker.mlflow:
        experiment_name: "image_classification"
        nested: True
```

## Working with Configuration Files

### Autogenerating Template YAML Files

ZenML provides a command to generate a template configuration file:

```bash
zenml pipeline build-configuration my_pipeline > config.yaml
```

This generates a YAML file with all pipeline parameters, step parameters, and configuration options with their default values.

### Environment Variables in Configuration

You can reference environment variables in your YAML configuration:

```yaml
settings:
  docker:
    environment:
      # References an environment variable from the host system
      API_KEY: ${MY_API_KEY}
      DATABASE_URL: ${DB_CONNECTION_STRING}
```

### Using Configuration Files for Different Environments

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

## Advanced Configuration Options

### Model Configuration

Link a pipeline to a ZenML Model:

```yaml
model:
  name: "classification_model"
  description: "Image classifier trained on the CIFAR-10 dataset"
  tags: ["computer-vision", "classification", "pytorch"]
  
  # Specific model version
  version: "1.2.3"
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
```

## Conclusion

YAML configuration in ZenML provides a powerful way to customize pipeline behavior without changing your code. By separating configuration from implementation, you can make your ML workflows more flexible, maintainable, and reproducible.

See also:
- [Steps & Pipelines](./steps_and_pipelines.md) - Core building blocks
- [Advanced Features](./advanced_features.md) - Advanced pipeline features