---
description: >-
  Learn how to control and customize logging behavior in ZenML pipelines.
---

# Logging

Effective logging is essential for monitoring, debugging, and auditing machine learning workflows. ZenML provides comprehensive logging capabilities that allow you to track pipeline execution, step outputs, and system events.

## Viewing Logs

### Dashboard Logs

The ZenML dashboard provides a central place to view logs for all pipeline runs:

1. Navigate to the **Runs** tab in the dashboard
2. Select a specific run to view its logs
3. You can view logs for the entire pipeline or filter by specific steps

### CLI Logs

You can view logs using the ZenML CLI:

```bash
# View logs for a specific pipeline run
zenml pipeline logs <PIPELINE_RUN_ID>

# View logs for a specific step in a pipeline run
zenml pipeline logs <PIPELINE_RUN_ID> --step-name <STEP_NAME>
```

### Python Client Logs

You can also access logs programmatically using the Python client:

```python
from zenml.client import Client

# Get logs for a specific pipeline run
run = Client().get_pipeline_run("<PIPELINE_RUN_ID>")
logs = run.get_logs()
print(logs)

# Get logs for a specific step
step_logs = run.get_logs(step_name="<STEP_NAME>")
print(step_logs)
```

## Logging Configuration

### Enabling or Disabling Logs Storage

You can control whether logs are stored in the ZenML database:

```python
# At pipeline level
@pipeline(enable_step_logs=True)
def my_pipeline():
    ...

# At step level
@step(enable_step_logs=True)
def my_step():
    ...
```

You can also configure this using a YAML file:

```yaml
enable_step_logs: True

steps:
  my_step:
    enable_step_logs: False
```

### Setting Logging Verbosity

You can control the verbosity level of ZenML logs:

```python
from zenml.logger import get_logger

# Set global logging level
import logging
logging.getLogger("zenml").setLevel(logging.DEBUG)

# Get a logger for a specific module
logger = get_logger(__name__)
logger.debug("This is a debug message")
logger.info("This is an info message")
logger.warning("This is a warning message")
logger.error("This is an error message")
```

You can also set the logging level using environment variables:

```bash
# Set logging level to DEBUG
export ZENML_LOGGING_VERBOSITY=DEBUG
```

Valid levels are: `NOTSET`, `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

### Setting Logging Format

You can customize the format of log messages:

```bash
# Set a custom log format
export ZENML_LOGGING_FORMAT="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

### Disabling Rich Traceback Output

ZenML uses rich tracebacks by default. You can disable them:

```bash
export ZENML_DISABLE_RICH_TRACEBACK=True
```

### Disabling Colorful Logging

To disable colorful logging output:

```bash
export ZENML_DISABLE_COLOR=True
```

## Logging in Steps

### Basic Logging

You can use Python's standard logging mechanism inside steps:

```python
from zenml import step
from zenml.logger import get_logger

logger = get_logger(__name__)

@step
def my_step():
    logger.info("Starting step execution")
    # Step logic
    logger.info("Step execution completed")
```

### Capturing Standard Output

Standard output and error streams are automatically captured and stored:

```python
@step
def my_step():
    print("This will be captured in the logs")
    # Step logic
```

### Structured Logging with Metadata

You can add structured metadata to your logs:

```python
from zenml import step, log_artifact_metadata

@step
def train_model() -> None:
    model = train()
    
    # Log metadata about the training
    log_artifact_metadata(
        metadata={
            "accuracy": 0.95,
            "f1_score": 0.94,
            "training_time": 120,
        },
        artifact_name="model"
    )
```

### Logging Metrics

For more advanced metrics tracking, you can use experiment trackers:

```python
from zenml import step
from zenml.client import Client

@step(experiment_tracker="mlflow")
def train_model():
    # Get the active experiment tracker
    tracker = Client().active_stack.experiment_tracker
    
    # Log metrics
    tracker.log_metric("accuracy", 0.95)
    tracker.log_metric("f1_score", 0.94)
```

## Best Practices for Logging

1. **Use appropriate log levels**:
   - `DEBUG`: Detailed information for diagnosing problems
   - `INFO`: Confirmation that things are working as expected
   - `WARNING`: Indication that something unexpected happened
   - `ERROR`: Due to a more serious problem, software hasn't been able to perform a function
   - `CRITICAL`: A serious error, indicating program may be unable to continue running

2. **Include contextual information** in log messages to make them more useful for debugging

3. **Log at decision points** to help understand the flow of execution

4. **Avoid logging sensitive information** like passwords, tokens, or personal data

5. **Use structured logging** when appropriate to make logs more searchable and analyzable

6. **Configure appropriate verbosity** based on the environment (more verbose in development, less in production)

## Accessing Logs Programmatically

You can access logs programmatically for automation or analysis:

```python
from zenml.client import Client

# Get all pipeline runs
runs = Client().list_pipeline_runs()

# Get logs for each run
for run in runs:
    logs = run.get_logs()
    # Process logs
```

## Conclusion

Effective logging is crucial for developing, monitoring, and maintaining ML pipelines. ZenML provides flexible logging capabilities that can be tailored to your specific needs, from basic debugging to detailed performance tracking.

By configuring logging appropriately and following best practices, you can gain valuable insights into your pipeline execution and quickly identify and resolve issues when they arise.

See also:
- [Steps & Pipelines](./steps_and_pipelines.md) - Core building blocks
- [Configuration & Settings](./configuration_settings.md) - YAML configuration
- [Execution Parameters](./execution_parameters.md) - Runtime parameters 