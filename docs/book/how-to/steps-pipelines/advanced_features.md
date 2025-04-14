---
description: Advanced features and capabilities of ZenML pipelines and steps
---

# Advanced Features

This guide covers advanced features and capabilities of ZenML pipelines and steps, allowing you to build more sophisticated machine learning workflows.

## Configuration & Customization

ZenML offers multiple ways to configure and customize your pipelines and steps. This section explains the different configuration options available.

### Ways to Apply Configuration

ZenML provides several approaches to configure your pipelines and steps:

#### 1. Step-Level Configuration

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

#### 2. Direct Component Assignment

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

#### 3. Pipeline Configuration with `configure`

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

#### 4. Runtime Configuration with `with_options`

You can configure a pipeline at runtime using the `with_options` method:

```python
# Configure specific step parameters
my_pipeline.with_options(steps={"trainer": {"parameters": {"learning_rate": 0.01}}})()

# Or using a YAML configuration file
my_pipeline.with_options(config_file="path_to_yaml_file")()
```

### Types of Settings

Settings in ZenML are categorized into two main types:

* **General settings** that can be used on all ZenML pipelines:
  * `DockerSettings` for container configuration
  * `ResourceSettings` for CPU, memory, and GPU allocation

* **Stack-component-specific settings** for configuring behaviors of components in your stack:
  * These use the pattern `<COMPONENT_CATEGORY>` or `<COMPONENT_CATEGORY>.<COMPONENT_FLAVOR>` as keys
  * Examples include `experiment_tracker.mlflow` or just `step_operator`

### Common Setting Types

#### Resource Settings

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

#### Docker Settings

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

### Stack Component Configuration

#### Registration-time vs Runtime Stack Component Settings

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

#### Using the Right Key for Stack Component Settings

When specifying stack-component-specific settings, the key follows this pattern:

```python
# Using just the component category
@step(settings={"step_operator": {"estimator_args": {"instance_type": "m7g.medium"}}})

# Or using the component category and flavor
@step(settings={"experiment_tracker.mlflow": {"experiment_name": "custom_experiment"}})
```

If you specify just the category (e.g., `step_operator`), ZenML applies these settings to whatever flavor of component is in your stack. If the settings don't apply to that flavor, they are ignored.

### Making Configurations Flexible with Environment Variables

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

## Type annotations

Your functions will work as ZenML steps even if you don't provide any type annotations for their inputs and outputs. However, adding type annotations to your step functions gives you lots of additional benefits:

* **Type validation of your step inputs**: ZenML makes sure that your step functions receive an object of the correct type from the upstream steps in your pipeline.
* **Better serialization**: Without type annotations, ZenML uses [Cloudpickle](https://github.com/cloudpipe/cloudpickle) to serialize your step outputs. When provided with type annotations, ZenML can choose a [materializer](https://docs.zenml.io/getting-started/core-concepts#materializers) that is best suited for the output. In case none of the builtin materializers work, you can even [write a custom materializer](https://docs.zenml.io/how-to/data-artifact-management/handle-data-artifacts/handle-custom-data-types).

{% hint style="warning" %}
ZenML provides a built-in [CloudpickleMaterializer](https://sdkdocs.zenml.io/latest/core_code_docs/core-materializers.html#zenml.materializers.cloudpickle_materializer) that can handle any object by saving it with [cloudpickle](https://github.com/cloudpipe/cloudpickle). However, this is not production-ready because the resulting artifacts cannot be loaded when running with a different Python version. In such cases, you should consider building a [custom Materializer](https://docs.zenml.io/how-to/data-artifact-management/handle-data-artifacts/handle-custom-data-types#custom-materializers) to save your objects in a more robust and efficient format.

Moreover, using the `CloudpickleMaterializer` could allow users to upload of any kind of object. This could be exploited to upload a malicious file, which could execute arbitrary code on the vulnerable system.
{% endhint %}

```python
from typing import Tuple
from zenml import step

@step
def square_root(number: int) -> float:
    return number ** 0.5

# To define a step with multiple outputs, use a `Tuple` type annotation
@step
def divide(a: int, b: int) -> Tuple[int, int]:
    return a // b, a % b
```

If you want to make sure you get all the benefits of type annotating your steps, you can set the environment variable `ZENML_ENFORCE_TYPE_ANNOTATIONS` to `True`. ZenML will then raise an exception in case one of the steps you're trying to run is missing a type annotation.

### Tuple vs multiple outputs

It is impossible for ZenML to detect whether you want your step to have a single output artifact of type `Tuple` or multiple output artifacts just by looking at the type annotation.

We use the following convention to differentiate between the two: When the `return` statement is followed by a tuple literal (e.g. `return 1, 2` or `return (value_1, value_2)`) we treat it as a step with multiple outputs. All other cases are treated as a step with a single output of type `Tuple`.

```python
from zenml import step
from typing_extensions import Annotated
from typing import Tuple

# Single output artifact
@step
def my_step() -> Tuple[int, int]:
    output_value = (0, 1)
    return output_value

# Single output artifact with variable length
@step
def my_step(condition) -> Tuple[int, ...]:
    if condition:
        output_value = (0, 1)
    else:
        output_value = (0, 1, 2)

    return output_value

# Single output artifact using the `Annotated` annotation
@step
def my_step() -> Annotated[Tuple[int, ...], "my_output"]:
    return 0, 1


# Multiple output artifacts
@step
def my_step() -> Tuple[int, int]:
    return 0, 1


# Not allowed: Variable length tuple annotation when using
# multiple output artifacts
@step
def my_step() -> Tuple[int, ...]:
    return 0, 1
```

## Step output names

By default, ZenML uses the output name `output` for single output steps and `output_0, output_1, ...` for steps with multiple outputs. These output names are used to display your outputs in the dashboard and [fetch them after your pipeline is finished](fetching-pipelines.md).

If you want to use custom output names for your steps, use the `Annotated` type annotation:

```python
from typing_extensions import Annotated  # or `from typing import Annotated on Python 3.9+
from typing import Tuple
from zenml import step

@step
def square_root(number: int) -> Annotated[float, "custom_output_name"]:
    return number ** 0.5

@step
def divide(a: int, b: int) -> Tuple[
    Annotated[int, "quotient"],
    Annotated[int, "remainder"]
]:
    return a // b, a % b
```

{% hint style="info" %}
If you do not give your outputs custom names, the created artifacts will be named `{pipeline_name}::{step_name}::output` or `{pipeline_name}::{step_name}::output_{i}` in the dashboard. See the [documentation on artifact versioning and configuration](https://docs.zenml.io/user-guides/starter-guide/manage-artifacts) for more information.
{% endhint %}

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

The fan-out/fan-in pattern is a common pipeline architecture where a single step splits into multiple parallel operations (fan-out) and then consolidates the results back into a single step (fan-in). This pattern is particularly useful for parallel processing, distributed workloads, or when you need to process data through different transformations and then aggregate the results. For example, you might want to process different chunks of data in parallel and then aggregate the results:

```python
from zenml import step, get_step_context, pipeline
from zenml.client import Client


@step
def load_step() -> str:
    return "Hello from ZenML!"


@step
def process_step(input_data: str) -> str:
    return input_data


@step
def combine_step(step_prefix: str, output_name: str) -> None:
    run_name = get_step_context().pipeline_run.name
    run = Client().get_pipeline_run(run_name)

    # Fetch all results from parallel processing steps
    processed_results = {}
    for step_name, step_info in run.steps.items():
        if step_name.startswith(step_prefix):
            output = step_info.outputs[output_name][0]
            processed_results[step_info.name] = output.load()

    # Combine all results
    print(",".join([f"{k}: {v}" for k, v in processed_results.items()]))


@pipeline(enable_cache=False)
def fan_out_fan_in_pipeline(parallel_count: int) -> None:
    # Initial step (source)
    input_data = load_step()

    # Fan out: Process data in parallel branches
    after = []
    for i in range(parallel_count):
        artifact = process_step(input_data, id=f"process_{i}")
        after.append(artifact)

    # Fan in: Combine results from all parallel branches
    combine_step(step_prefix="process_", output_name="output", after=after)


fan_out_fan_in_pipeline(parallel_count=8)
```

The fan-out pattern allows for parallel processing and better resource utilization, while the fan-in pattern enables aggregation and consolidation of results. This is particularly useful for:

- Parallel data processing
- Distributed model training
- Ensemble methods
- Batch processing
- Data validation across multiple sources
- [Hyperparameter tuning](./hyper-parameter-tuning.md)

Note that when implementing the fan-in step, you'll need to use the ZenML Client to query the results from previous parallel steps, as shown in the example above, and you can't pass in the result directly.

{% hint style="warning" %}
The fan-in, fan-out method has the following limitations:

1. Steps run sequentially rather than in parallel if the underlying orchestrator does not support parallel step runs (e.g. with the local orchestrator)
2. The number of steps need to be known ahead-of-time, and ZenML does not yet support the ability to dynamically create steps on the fly.
{% endhint %}

### Custom Step Invocation IDs

When calling a ZenML step as part of your pipeline, it gets assigned a unique **invocation ID** that you can use to reference this step invocation when [defining the execution order](control-execution-order-of-steps.md) of your pipeline steps or use it to [fetch information](fetching-pipelines.md) about the invocation after the pipeline has finished running.

```python
from zenml import pipeline, step

@step
def my_step() -> None:
    ...

@pipeline
def example_pipeline():
    # When calling a step for the first time inside a pipeline,
    # the invocation ID will be equal to the step name -> `my_step`.
    my_step()
    # When calling the same step again, the suffix `_2`, `_3`, ... will
    # be appended to the step name to generate a unique invocation ID.
    # For this call, the invocation ID would be `my_step_2`.
    my_step()
    # If you want to use a custom invocation ID when calling a step, you can
    # do so by passing it like this. If you pass a custom ID, it needs to be
    # unique for all the step invocations that happen as part of this pipeline.
    my_step(id="my_custom_invocation_id")
```

### Named Pipeline Runs

In the output logs of a pipeline run you will see the name of the run:

```bash
Pipeline run training_pipeline-2023_05_24-12_41_04_576473 has finished in 3.742s.
```

This name is automatically generated based on the current date and time. To change the name for a run, pass `run_name` as a parameter to the `with_options()` method:

```python
training_pipeline = training_pipeline.with_options(
    run_name="custom_pipeline_run_name"
)
training_pipeline()
```

Pipeline run names must be unique, so if you plan to run your pipelines multiple times or run them on a schedule, make sure to either compute the run name dynamically or include one of the placeholders that ZenML will replace.

{% hint style="info" %}
The substitutions for the custom placeholders like `experiment_name` can be set in:
- `@pipeline` decorator, so they are effective for all steps in this pipeline
- `pipeline.with_options` function, so they are effective for all steps in this pipeline run

Standard substitutions always available and consistent in all steps of the pipeline are:
- `{date}`: current date, e.g. `2024_11_27`
- `{time}`: current time in UTC format, e.g. `11_07_09_326492`
{% endhint %}

```python
training_pipeline = training_pipeline.with_options(
    run_name="custom_pipeline_run_name_{experiment_name}_{date}_{time}"
)
training_pipeline()
```

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

| Orchestrator                                                                     | Scheduling Support |
|----------------------------------------------------------------------------------|--------------------|
| [AirflowOrchestrator](https://docs.zenml.io/stacks/orchestrators/airflow)            | ✅                 |
| [AzureMLOrchestrator](https://docs.zenml.io/stacks/orchestrators/azureml)            | ✅                 |
| [DatabricksOrchestrator](https://docs.zenml.io/stacks/orchestrators/databricks)      | ✅                 |
| [HyperAIOrchestrator](https://docs.zenml.io/stacks/orchestrators/hyperai)            | ✅                 |
| [KubeflowOrchestrator](https://docs.zenml.io/stacks/orchestrators/kubeflow)          | ✅                 |
| [KubernetesOrchestrator](https://docs.zenml.io/stacks/orchestrators/kubernetes)      | ✅                 |
| [LocalOrchestrator](https://docs.zenml.io/stacks/orchestrators/local)                | ⛔️                 |
| [LocalDockerOrchestrator](https://docs.zenml.io/stacks/orchestrators/local-docker)   | ⛔️                 |
| [SagemakerOrchestrator](https://docs.zenml.io/stacks/orchestrators/sagemaker)        | ✅                  |
| [SkypilotAWSOrchestrator](https://docs.zenml.io/stacks/orchestrators/skypilot-vm)    | ⛔️                 |
| [SkypilotAzureOrchestrator](https://docs.zenml.io/stacks/orchestrators/skypilot-vm)  | ⛔️                 |
| [SkypilotGCPOrchestrator](https://docs.zenml.io/stacks/orchestrators/skypilot-vm)    | ⛔️                 |
| [SkypilotLambdaOrchestrator](https://docs.zenml.io/stacks/orchestrators/skypilot-vm) | ⛔️                 |
| [TektonOrchestrator](https://docs.zenml.io/stacks/orchestrators/tekton)              | ⛔️                 |
| [VertexOrchestrator](https://docs.zenml.io/stacks/orchestrators/vertex)              | ✅                 |

### Managing Schedule Lifecycle

The way pipelines are scheduled depends on the orchestrator you are using. For example, if you are using Kubeflow, you can use the Kubeflow UI to stop or pause a scheduled run. However, the exact steps for stopping or pausing a scheduled run may vary depending on the orchestrator you are using. We recommend consulting the documentation for your orchestrator to learn the current method for stopping or pausing a scheduled run.

The normal pattern for updating a schedule is:

1. Find schedule on ZenML
2. Match schedule on orchestrator side and delete
3. Delete schedule on ZenML
4. Re-run pipeline with new schedule

A concrete example can be found on the [GCP Vertex orchestrator](https://docs.zenml.io/stacks/orchestrators/vertex) docs, and this pattern can be adapted for other orchestrators as well.

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


## Conclusion

These advanced features provide powerful capabilities for building sophisticated machine learning workflows in ZenML. By leveraging these features, you can create pipelines that are more robust, maintainable, and flexible.

See also:
- [Steps & Pipelines](./steps_and_pipelines.md) - Core building blocks
- [Configuration with YAML](./configuration_with_yaml.md) - YAML configuration 
