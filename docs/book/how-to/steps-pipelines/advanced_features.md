---
description: Advanced features and capabilities of ZenML pipelines and steps
---

# Advanced Features

This guide covers advanced features and capabilities of ZenML pipelines and steps, allowing you to build more sophisticated machine learning workflows.

## Execution Control

### Caching

Steps are automatically cached based on their inputs. When a step runs, ZenML computes a hash of the inputs and checks if a previous run with the same inputs exists. If found, ZenML reuses the outputs instead of re-executing the step.

You can control caching behavior at the step level:

```python
@step(enable_cache=False)
def non_cached_step():
    pass
```

You can also configure caching at the pipeline level:

```python
@pipeline(enable_cache=False)
def my_pipeline():
    ...
```

Or modify it after definition:

```python
my_step.configure(enable_cache=False)
my_pipeline.configure(enable_cache=False)
```

Cache invalidation happens automatically when:
- Step inputs change
- Step code changes
- Step configuration changes (parameters, settings, etc.)

### Running Individual Steps

You can run a single step directly:

```python
model, accuracy = train_classifier(X_train=X_train, y_train=y_train)
```

This creates an unlisted pipeline run with just that step. If you want to bypass ZenML completely and run the underlying function directly:

```python
model, accuracy = train_classifier.entrypoint(X_train=X_train, y_train=y_train)
```

You can make this the default behavior by setting the `ZENML_RUN_SINGLE_STEPS_WITHOUT_STACK` environment variable to `True`.

### Asynchronous Pipeline Execution

By default, pipelines run synchronously, with terminal logs displaying as the pipeline builds and runs. You can change this behavior to run pipelines asynchronously (in the background):

```python
from zenml import pipeline

@pipeline(settings={"orchestrator": {"synchronous": False}})
def my_pipeline():
    ...
```

Alternatively, you can configure this in a YAML config file:

```yaml
settings:
  orchestrator.<STACK_NAME>:
    synchronous: false
```

You can also configure the orchestrator to always run asynchronously by setting `synchronous=False` in its configuration.

### Step Execution Order

By default, ZenML determines step execution order based on data dependencies. When a step requires output from another step, it automatically creates a dependency.

You can explicitly control execution order with the `after` parameter:

```python
@pipeline
def my_pipeline():
    step_a_output = step_a()
    step_b_output = step_b()
    
    # step_c will only run after both step_a and step_b complete, even if
    # it doesn't use their outputs directly
    step_c(after=[step_a_output, step_b_output])
    
    # You can also specify dependencies using the step invocation ID
    step_d(after="step_c")
```

This is particularly useful for steps with side effects (like data loading or model deployment) where the data dependency is not explicit.

## Data & Output Management

### Tuple vs Multiple Outputs

ZenML needs to differentiate between a step with a single output of type `Tuple` and a step with multiple outputs. The system uses the following convention:

- When the `return` statement is followed by a tuple literal (e.g., `return 1, 2` or `return (value_1, value_2)`), it's treated as a step with multiple outputs
- All other cases are treated as a step with a single output of type `Tuple`

```python
from zenml import step
from typing_extensions import Annotated
from typing import Tuple

# Single output artifact
@step
def my_step() -> Tuple[int, int]:
    output_value = (0, 1)
    return output_value

# Multiple output artifacts
@step
def my_step() -> Tuple[int, int]:
    return 0, 1  # or return (0, 1)
```

### Custom Output Names

By default, step outputs are named `output` for single output steps and `output_0`, `output_1`, etc. for steps with multiple outputs. You can name your step outputs using the `Annotated` type:

```python
from typing_extensions import Annotated  # or `from typing import Annotated` on Python 3.9+
from typing import Tuple

@step
def divide(a: int, b: int) -> Tuple[
    Annotated[int, "quotient"],
    Annotated[int, "remainder"]
]:
    return a // b, a % b
```

These custom names make it easier to identify outputs in the dashboard and when fetching them programmatically.

### Type Annotations

While optional, type annotations are highly recommended and provide several benefits:
* **Artifact handling**: ZenML uses type annotations to determine how to serialize, store, and load artifacts. The type information guides ZenML to select the appropriate materializer for saving and loading step outputs.
* **Type validation**: ZenML validates inputs against type annotations at runtime to catch errors early.
* **Code documentation**: Types make your code more self-documenting and easier to understand.

```python
from typing import Tuple

@step
def square_root(number: int) -> float:
    return number ** 0.5

@step
def divide(a: int, b: int) -> Tuple[int, int]:
    return a // b, a % b
```

When you specify a return type like `-> float` or `-> Tuple[int, int]`, ZenML uses this information to determine how to store the step's output in the artifact store. For instance, a step returning a pandas DataFrame with the annotation `-> pd.DataFrame` will use the pandas-specific materializer for efficient storage.

If you want to enforce type annotations for all steps, set the environment variable `ZENML_ENFORCE_TYPE_ANNOTATIONS` to `True`.

## Workflow Patterns

### Pipeline Composition

You can compose pipelines from other pipelines to create modular, reusable workflows:

```python
@pipeline
def data_pipeline(mode: str):
    if mode == "train":
        data = training_data_loader_step()
    else:
        data = test_data_loader_step()
    
    processed_data = preprocessing_step(data)
    return processed_data

@pipeline
def training_pipeline():
    # Use another pipeline inside this pipeline
    training_data = data_pipeline(mode="train")
    model = train_model(data=training_data)
    test_data = data_pipeline(mode="test")
    evaluate_model(model=model, data=test_data)
```

Pipeline composition allows you to build complex workflows from simpler, well-tested components.

### Fan-in and Fan-out

You can implement parallel processing patterns for data-parallel workloads:

```python
@pipeline
def fan_pipeline():
    # Fan-out: Process data chunks in parallel
    results = []
    for i in range(5):
        results.append(process_chunk(i))
    
    # Fan-in: Combine all results
    final_result = combine_results(results)
```

When run on an orchestrator that supports parallelism (like Kubeflow), the `process_chunk` steps can run in parallel, improving performance for data-parallel workloads.

### Custom Step Invocation IDs

By default, ZenML uses the function name as the step invocation ID. For steps used multiple times, you should specify a custom ID:

```python
@pipeline
def my_pipeline():
    # Custom invocation ID "first_step"
    first_output = my_step(step_name="first_step")
    # Custom invocation ID "second_step"
    second_output = my_step(step_name="second_step")
```

This makes the pipeline easier to understand and helps with debugging and monitoring.

### Named Pipeline Runs

You can give your pipeline runs descriptive names to make them easier to identify:

```python
from datetime import datetime

run_name = f"training_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
my_pipeline.with_options(run_name=run_name)()
```

This is especially useful in production environments where you need to track and monitor specific runs.

## Scheduling

Scheduling allows you to run pipelines automatically at specified times or intervals, which is essential for production ML workflows that need regular retraining or inference.

### Setting Up a Schedule

You can schedule a pipeline using either cron expressions or time intervals:

```python
from zenml.config.schedule import Schedule
from zenml import pipeline
from datetime import datetime

@pipeline()
def my_pipeline(...):
    ...

# Use cron expressions
schedule = Schedule(cron_expression="5 14 * * 3")  # Runs at 2:05 PM every Wednesday

# Or use human-readable time intervals
schedule = Schedule(start_time=datetime.now(), interval_second=1800)  # Runs every 30 minutes

# Apply the schedule when running the pipeline
my_pipeline = my_pipeline.with_options(schedule=schedule)
my_pipeline()
```

### Supported Orchestrators

Not all orchestrators support scheduling. Here's a compatibility overview:

| Orchestrator Type | Scheduling Support |
|-------------------|--------------------|
| Local/Docker      | ❌ Not supported   |
| Kubernetes-based  | ✅ Supported       |
| Cloud-managed     | ✅ Supported       |
| Airflow           | ✅ Supported       |

To see the full list of supported orchestrators, check the [scheduling documentation](https://docs.zenml.io/how-to/pipeline-development/build-pipelines/schedule-a-pipeline).

### Managing Schedule Lifecycle

Managing existing schedules depends on your orchestrator. The general workflow for updating schedules is:

1. Find your schedule in ZenML
2. Match and delete the schedule on the orchestrator side
3. Delete the schedule in ZenML
4. Re-run the pipeline with the new schedule

```python
# Example of updating a schedule
from zenml.client import Client

# Find the existing schedule
client = Client()
schedules = client.list_pipeline_schedules()

# Delete the existing schedule
# Note: You also need to delete the schedule on the orchestrator side
client.delete_schedule(schedule_id="your-schedule-id")

# Create and run with a new schedule
new_schedule = Schedule(cron_expression="0 9 * * *")  # Daily at 9 AM
my_pipeline.with_options(schedule=new_schedule)()
```

### Best Practices

* Use descriptive names for scheduled pipelines to easily identify them
* Consider time zones when setting up cron schedules
* Set up monitoring to detect and alert on failed scheduled runs
* For production pipelines, include retry logic to handle transient failures
* Document your schedule configurations for team reference

### Scheduling Limitations

* Running a pipeline with a schedule multiple times will create multiple scheduled instances
* ZenML only handles initial schedule creation, not ongoing management
* For advanced scheduling needs (dependencies, conditional execution), consider using an orchestrator like Airflow directly

## Error Handling & Reliability

### Automatic Step Retries

For steps that may encounter transient failures (like network issues or resource limitations), you can configure automatic retries:

```python
from zenml.config.retry_config import StepRetryConfig

@step(
    retry=StepRetryConfig(
        max_retries=3,  # Maximum number of retry attempts
        delay=10,       # Initial delay in seconds before first retry
        backoff=2       # Factor by which delay increases after each retry
    )
)
def unreliable_step():
    # This step might fail due to transient issues
    ...
```

With this configuration, if the step fails, ZenML will:
1. Wait 10 seconds before the first retry
2. Wait 20 seconds (10 × 2) before the second retry
3. Wait 40 seconds (20 × 2) before the third retry
4. Fail the pipeline if all retries are exhausted

This is particularly useful for steps that interact with external services or resources.

## Monitoring & Notifications

### Pipeline and Step Hooks

Hooks allow you to execute custom code at specific points in the pipeline or step lifecycle:

```python
def success_hook(step_name, step_output):
    print(f"Step {step_name} completed successfully with output: {step_output}")

def failure_hook(exception: BaseException):
    print(f"Step failed with error: {str(exception)}")

@step(on_success=success_hook, on_failure=failure_hook)
def my_step():
    return 42
```

You can also define hooks at the pipeline level to apply to all steps:

```python
@pipeline(on_failure=failure_hook, on_success=success_hook)
def my_pipeline():
    ...
```

Step-level hooks take precedence over pipeline-level hooks. Hooks are particularly useful for:
- Sending notifications when steps fail or succeed
- Logging detailed information about runs
- Triggering external workflows based on pipeline state

### Accessing Step Context in Hooks

You can access detailed information about the current run using the step context:

```python
from zenml import step, get_step_context

def on_failure(exception: BaseException):
    context = get_step_context()
    print(f"Failed step: {context.step_run.name}")
    print(f"Parameters: {context.step_run.config.parameters}")
    print(f"Exception: {type(exception).__name__}: {str(exception)}")
    
    # Access pipeline information
    print(f"Pipeline: {context.pipeline_run.name}")

@step(on_failure=on_failure)
def my_step(some_parameter: int = 1):
    raise ValueError("My exception")
```

### Using Alerter in Hooks

You can use the Alerter stack component to send notifications when steps fail or succeed:

```python
from zenml import get_step_context
from zenml.client import Client

def on_failure():
    step_name = get_step_context().step_run.name
    Client().active_stack.alerter.post(f"{step_name} just failed!")
```

ZenML provides built-in alerter hooks for common scenarios:

```python
from zenml.hooks import alerter_success_hook, alerter_failure_hook

@step(on_failure=alerter_failure_hook, on_success=alerter_success_hook)
def my_step():
    ...
```

## Configuration & Customization

### Step Settings

You can configure additional settings for steps beyond the basic parameters:

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

### Configuring Stack Components per Step

You can use different stack components for different steps:

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

### Advanced Pipeline Configuration

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

### Environment Variables in Configurations

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

### Runtime Configuration of Pipelines

You can configure a pipeline at runtime using the `with_options` method:

```python
# Configure specific step parameters
my_pipeline.with_options(steps={"trainer": {"parameters": {"learning_rate": 0.01}}})()

# Or using a YAML configuration file
my_pipeline.with_options(config_file="path_to_yaml_file")()
```

For triggering pipelines from a client or another pipeline, you can use a `PipelineRunConfiguration` object. This approach is covered in the [advanced template usage documentation](https://docs.zenml.io/how-to/trigger-pipelines/use-templates-python#advanced-usage-run-a-template-from-another-pipeline).

## Conclusion

These advanced features provide powerful capabilities for building sophisticated machine learning workflows in ZenML. By leveraging these features, you can create pipelines that are more robust, maintainable, and flexible.

See also:
- [Steps & Pipelines](./steps_and_pipelines.md) - Core building blocks
- [Configuration with YAML](./configuration_with_yaml.md) - YAML configuration 
