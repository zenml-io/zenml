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

## What Can Be Configured

### Pipeline and Step Parameters

You can specify parameters for pipelines and steps, allowing you to modify behavior without changing code:

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

This corresponds to code that looks like:

```python
@step
def preprocessing(normalize: bool, fill_missing: str):
    # Use parameters to control preprocessing behavior
    pass

@step
def train_model(learning_rate: float, optimizer: str):
    # Use parameters to configure model training
    pass

@pipeline
def my_pipeline(dataset_name: str, learning_rate: float, batch_size: int, epochs: int):
    # Use pipeline parameters
    data = load_data(dataset_name)
    processed_data = preprocessing(normalize=True, fill_missing="mean")
    train_model(learning_rate=learning_rate, optimizer="adam")
```

Parameters defined in YAML files override default values in the code, giving you flexibility to change behavior without modifying code.

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

Configure Docker container settings for pipeline execution, controlling the environment where your steps run:

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

Docker settings give you fine-grained control over the execution environment, ensuring consistent dependencies and resources across different machines and environments.

### Resource Settings

Configure compute resources for pipeline or step execution, particularly important for resource-intensive workloads:

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

Resource settings are especially important for:
- **Training steps**: Allocate more GPUs and memory for model training
- **Preprocessing steps**: Allocate more CPUs for data-parallel processing
- **Inference steps**: Balance resources based on throughput requirements

These settings are interpreted differently depending on the orchestrator (Kubernetes, Vertex AI, etc.) and can help optimize resource utilization.

### Stack Component Settings

Configure specific stack components for steps, allowing different steps to use different infrastructure:

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

This allows you to:
- Use different experiment trackers for different steps
- Route compute-intensive steps to specialized hardware
- Configure component-specific behavior for each step

### Model Configuration

Link a pipeline to a ZenML Model to integrate with the ZenML Model Control Plane:

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

This configuration allows you to:
- Track which pipelines produce which models
- Link specific artifacts to model versions
- Manage model metadata and lineage
- Compare model versions across multiple runs

### Run Name

Set a custom name for the pipeline run for easier identification and tracking:

```yaml
run_name: "training_run_cifar10_resnet50_lr0.001"
```

Descriptive run names help you:
- Identify specific runs in the UI or dashboard
- Understand the purpose of a run without digging into details
- Organize runs for different experiments or purposes

### Scheduling

Configure pipeline scheduling when using an orchestrator that supports it (like Airflow or Kubeflow):

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

Scheduling allows you to:
- Automate recurring workflows (daily data processing, weekly model retraining)
- Set up consistent evaluation or monitoring jobs
- Coordinate with other data pipelines in your organization

## Configuration Hierarchy and Resolution

ZenML follows a specific hierarchy when resolving configuration, using a clear precedence order:

1. **Runtime Python code** - Highest precedence
   ```python
   my_pipeline(learning_rate=0.01)  # Highest precedence
   ```

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
   ```python
   @step
   def train_model(learning_rate: float = 0.1):  # Lowest precedence
       pass
   ```

This resolution strategy gives you flexibility to:
- Set sensible defaults in code
- Override defaults in configuration files
- Make quick changes at runtime

Understanding this hierarchy helps you manage configurations more effectively and avoid unexpected behavior.

## Autogenerating Template YAML Files

ZenML provides a command to generate a template configuration file based on your pipeline definition:

```bash
zenml pipeline build-configuration my_pipeline > config.yaml
```

This generates a YAML file with:
- All pipeline parameters with their default values
- All step parameters with their default values
- All possible configuration options (enable flags, settings, etc.)

You can then customize this template for your specific needs, saving time and reducing errors.

## Environment Variables in Configuration

You can reference environment variables in your YAML configuration, which is useful for sensitive information or environment-specific settings:

```yaml
settings:
  docker:
    environment:
      # References an environment variable from the host system
      API_KEY: ${MY_API_KEY}
      DATABASE_URL: ${DB_CONNECTION_STRING}
```

This approach allows you to:
- Keep sensitive information out of your configuration files
- Switch configurations based on environment variables
- Integrate with secrets management systems

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

This approach allows you to:
- Use different resources in different environments
- Apply different caching strategies
- Use smaller datasets for rapid development
- Apply stricter settings in production

## Finding Which Configuration Was Used for a Run

To determine which configuration was used for a specific run, you can access it programmatically:

```python
from zenml.client import Client

# Get a specific pipeline run
run = Client().get_pipeline_run("<RUN_ID>")

# Access the configuration
config = run.config

# Print specific configuration values
print(f"Learning rate: {config.parameters.get('learning_rate')}")
print(f"Cache enabled: {config.enable_cache}")

# Access step-specific configuration
train_step_config = config.steps.get("train_model", {})
print(f"Train step learning rate: {train_step_config.parameters.get('learning_rate')}")
```

This allows you to:
- Reproduce the exact configuration used for a specific run
- Compare configurations across different runs
- Audit runs for compliance or debugging

## Conclusion

Configuration and settings in ZenML provide a powerful way to customize pipeline behavior without changing your code. By leveraging YAML configuration files, you can separate configuration from implementation, making your ML workflows more flexible, maintainable, and reproducible.

The right configuration approach allows you to:
- Iterate quickly during development
- Ensure consistency in production
- Share workflows with team members
- Track and reproduce experiments

See also:
- [Steps & Pipelines](./steps_and_pipelines.md) - Core building blocks
- [Execution Parameters](./execution_parameters.md) - Runtime parameters
- [Logging](./logging.md) - Logging configuration 