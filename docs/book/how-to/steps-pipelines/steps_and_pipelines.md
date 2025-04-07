---
description: Steps and Pipelines are the core building blocks of ZenML
---

# Steps & Pipelines

Steps and Pipelines are the fundamental building blocks of ZenML. A **Step** is a reusable unit of computation, and a **Pipeline** is a directed acyclic graph (DAG) composed of steps. Together, they allow you to define, version, and execute machine learning workflows.

## Creating Steps

A step is created by applying the `@step` decorator to a Python function:

```python
from zenml import step

@step
def load_data() -> dict:
    training_data = [[1, 2], [3, 4], [5, 6]]
    labels = [0, 1, 0]
    return {'features': training_data, 'labels': labels}
```

### Step Inputs and Outputs

Steps can take inputs and produce outputs. These can be simple types, complex data structures, or custom objects.

```python
@step
def train_model(data: dict) -> None:
    total_features = sum(map(sum, data['features']))
    total_labels = sum(data['labels'])
    print(f"Trained model using {len(data['features'])} data points. "
          f"Feature sum is {total_features}, label sum is {total_labels}")
```

### Type Annotations

While optional, type annotations provide several benefits:
- Type validation for step inputs
- Better serialization via appropriate materializers
- Clearer code documentation

```python
from typing import Tuple

@step
def square_root(number: int) -> float:
    return number ** 0.5

@step
def divide(a: int, b: int) -> Tuple[int, int]:
    return a // b, a % b
```

If you want to enforce type annotations for all steps, set the environment variable `ZENML_ENFORCE_TYPE_ANNOTATIONS` to `True`.

### Custom Output Names

You can name your step outputs using the `Annotated` type:

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

By default, step outputs are named `output` for single output steps and `output_0`, `output_1`, etc. for steps with multiple outputs.

### Multiple Return Values

Steps can return multiple artifacts:

```python
from typing import Tuple
from sklearn.base import ClassifierMixin
from typing_extensions import Annotated

@step
def train_classifier(X_train, y_train) -> Tuple[
    Annotated[ClassifierMixin, "model"],
    Annotated[float, "accuracy"]
]:
    model = SVC(gamma=0.001)
    model.fit(X_train, y_train)
    accuracy = model.score(X_train, y_train)
    return model, accuracy
```

ZenML uses the following convention to differentiate between a single output of type `Tuple` and multiple outputs:
- When the `return` statement is followed by a tuple literal (e.g., `return 1, 2` or `return (value_1, value_2)`), it's treated as a step with multiple outputs
- All other cases are treated as a step with a single output of type `Tuple`

## Creating Pipelines

A pipeline is created by applying the `@pipeline` decorator to a Python function that composes steps together:

```python
from zenml import pipeline

@pipeline
def simple_ml_pipeline():
    dataset = load_data()
    train_model(dataset)
```

### Running Pipelines

You can run a pipeline by simply calling the function:

```python
simple_ml_pipeline()
```

The run is automatically logged to the ZenML dashboard where you can view the DAG and associated metadata.

## Pipeline and Step Parameters

Steps and pipelines can be parameterized like regular Python functions:

```python
@step
def my_step(input_1: int, input_2: int) -> None:
    pass

@pipeline
def my_pipeline(environment: str):
    my_step(input_1=42, input_2=43)
```

### Parameter vs. Artifact Inputs

When calling a step in a pipeline, inputs can be either:
- **Parameters**: Values provided explicitly when invoking a step. Only JSON-serializable values can be passed as parameters.
- **Artifacts**: Outputs from other steps in the same pipeline.

```python
@pipeline
def my_pipeline():
    int_artifact = some_other_step()
    # input_1 is an artifact, input_2 is a parameter
    my_step(input_1=int_artifact, input_2=42)
```

## Advanced Pipeline Features

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

## Conclusion

Steps and Pipelines provide a flexible, powerful way to build machine learning workflows in ZenML. By combining steps into pipelines, you can create complex ML processes that are versioned, reproducible, and easily monitored through the ZenML dashboard.

For more advanced configuration options, check out the [Configuration & Settings](./configuration_settings.md) and [Execution Parameters](./execution_parameters.md) guides. 