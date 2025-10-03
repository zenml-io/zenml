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

This creates an [unlisted pipeline run](https://docs.zenml.io/user-guides/best-practices/keep-your-dashboard-server-clean#unlisted-runs) with just that step. If you want to bypass ZenML completely and run the underlying function directly:

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

### Execution Modes

ZenML provides three execution modes that control how your orchestrator behaves when a step fails during pipeline execution. These modes are:

- `CONTINUE_ON_FAILURE`: The orchestrator continues executing steps that don't depend on any of the failed steps.
- `STOP_ON_FAILURE`: The orchestrator allows the running steps to complete, but prevents new steps from starting. 
- `FAIL_FAST`: The orchestrator stops the run and any running steps immediately when a failure occurs.

You can configure the execution mode of your pipeline in several ways:

```python
from zenml import pipeline
from zenml.enums import ExecutionMode

# Use the decorator
@pipeline(execution_mode=ExecutionMode.CONTINUE_ON_ERROR)
def my_pipeline():
    ...

# Use the `with_options` method
my_pipeline_with_fail_fast = my_pipeline.with_options(
    execution_mode=ExecutionMode.FAIL_FAST
)

# Use the `configure` method
my_pipeline.configure(execution_mode=ExecutionMode.STOP_ON_FAILURE)
```

{% hint style="warning" %}
In the current implementation, if you use the execution mode `STOP_ON_FAILURE`, the token that is associated with your pipeline run stays valid until its leeway runs out (defaults to 1 hour).
{% endhint %}

As an example, you can consider a pipeline with this dependency structure:

```
         ┌─► Step 2 ──► Step 5 ─┐
Step 1 ──┼─► Step 3 ──► Step 6 ─┼──► Step 8
         └─► Step 4 ──► Step 7 ─┘
```

If steps 2, 3, and 4 execute in parallel and step 2 fails:

- With `FAIL_FAST`: Step 1 finishes → Steps 2,3,4 start → Step 2 fails → Steps 3, 4 are stopped → No other steps get launched
- With `STOP_ON_FAILURE`: Step 1 finishes → Steps 2,3,4 start → Step 2 fails but Steps 3, 4 complete → Steps 5, 6, 7 are skipped
- With `CONTINUE_ON_FAILURE`: Step 1 finishes → Steps 2,3,4 start → Step 2 fails, Steps 3, 4 complete → Step 5 skipped (depends on failed Step 2), Steps 6, 7 run normally → Step 8 is skipped as well.

{% hint style="info" %}
All three execution modes are currently only supported by the `local`, `local_docker`, and `kubernetes` orchestrator flavors. For any other orchestrator flavor, the default (and only available) behavior is `CONTINUE_ON_FAILURE`. If you would like to see any of the other orchestrators extended to support the other execution modes, reach out to us in [Slack](https://zenml.io/slack-invite). 
{% endhint %}

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
from typing import Annotated
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

By default, ZenML uses the output name `output` for single output steps and `output_0, output_1, ...` for steps with multiple outputs. These output names are used to display your outputs in the dashboard and [fetch them after your pipeline is finished](https://docs.zenml.io/user-guides/tutorial/fetching-pipelines).

If you want to use custom output names for your steps, use the `Annotated` type annotation:

```python
from typing import Annotated
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

### Fan-out and Fan-in

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
- Hyperparameter tuning

Note that when implementing the fan-in step, you'll need to use the ZenML Client to query the results from previous parallel steps, as shown in the example above, and you can't pass in the result directly.

{% hint style="warning" %}
The fan-in, fan-out method has the following limitations:

1. Steps run sequentially rather than in parallel if the underlying orchestrator does not support parallel step runs (e.g. with the local orchestrator)
2. The number of steps need to be known ahead-of-time, and ZenML does not yet support the ability to dynamically create steps on the fly.
{% endhint %}

### Dynamic Fan-out/Fan-in with Snapshots

For scenarios where you need to determine the number of parallel operations at runtime (e.g., based on database queries or dynamic data), you can use [snapshots](https://docs.zenml.io/user-guides/tutorial/trigger-pipelines-from-external-systems) to create a more flexible fan-out/fan-in pattern. This approach allows you to trigger multiple pipeline runs dynamically and then aggregate their results.

```python
from typing import List, Optional
from uuid import UUID
import time

from zenml import step, pipeline
from zenml.client import Client


@step
def load_relevant_chunks() -> List[str]:
    """Load chunk identifiers from database or other dynamic source."""
    # Example: Query database for chunk IDs
    # In practice, this could be a database query, API call, etc.
    return ["chunk_1", "chunk_2", "chunk_3", "chunk_4"]


@step
def trigger_chunk_processing(
    chunks: List[str], 
    snapshot_id: Optional[UUID] = None
) -> List[UUID]:
    """Trigger multiple pipeline runs for each chunk and wait for completion."""
    client = Client()
    
    # Use snapshot ID if provided, otherwise give the pipeline name 
    # of the pipeline you want triggered. Giving the pipeline name
    # will automatically find the latest snapshot of that pipeline.
    pipeline_name = None if snapshot_id else "chunk_processing_pipeline"
    
    # Trigger all chunk processing runs
    run_ids = []
    for chunk_id in chunks:
        run_config = {
            "steps": {
                "process_chunk": {
                    "parameters": {
                        "chunk_id": chunk_id
                    }
                }
            }
        }
        
        run = client.trigger_pipeline(
            snapshot_name_or_id=snapshot_id,
            pipeline_name_or_id=pipeline_name,
            run_configuration=run_config,
            synchronous=False  # Run asynchronously
        )
        run_ids.append(run.id)
    
    # Wait for all runs to complete
    print(f"Waiting for {len(run_ids)} chunk processing runs to complete...")
    completed_runs = set()  # Cache completed runs to avoid re-fetching
    while True:
        # Only check runs that haven't completed yet
        pending_runs = [run_id for run_id in run_ids if run_id not in completed_runs]
        
        for run_id in pending_runs:
            run = client.get_pipeline_run(run_id)
            if run.status.is_finished:
                completed_runs.add(run_id)
        
        if len(completed_runs) == len(run_ids):
            print("All chunk processing runs completed!")
            break
        
        print(f"Completed: {len(completed_runs)}/{len(run_ids)} runs")
        time.sleep(10)  # Wait 10 seconds before checking again
    
    return run_ids


@step
def aggregate_results(run_ids: List[UUID]) -> dict:
    """Aggregate results from all chunk processing runs."""
    client = Client()
    aggregated_results = {}
    failed_runs = []
    
    for run_id in run_ids:
        run = client.get_pipeline_run(run_id)
        
        # Check if run succeeded
        if run.status.value == "failed":
            failed_runs.append({
                "run_id": str(run_id),
                "status": run.status.value,
            })
            print(f"WARNING: Run {run_id} failed with status {run.status.value}")
            continue
        
        # Extract results from successful runs only
        if "process_chunk" in run.steps:
            step_run = run.steps["process_chunk"]
            # Simple assumption: process_chunk step has one output that we can load
            chunk_result = step_run.output.load()
            aggregated_results[str(run_id)] = chunk_result

    
    # Log summary of results
    total_runs = len(run_ids)
    successful_runs = len(aggregated_results)
    failed_count = len(failed_runs)
    
    print(f"Aggregation complete: {successful_runs}/{total_runs} runs successful")

    return {
        "successful_results": aggregated_results,
        "failed_runs": failed_runs,
        "summary": {
            "total_runs": total_runs,
            "successful_runs": successful_runs,
            "failed_runs": failed_count
        }
    }


@pipeline(enable_cache=False)
def fan_out_fan_in_pipeline(snapshot_id: Optional[UUID] = None):
    """Fan-out/fan-in pipeline that orchestrates dynamic chunk processing."""
    # Load chunks dynamically at runtime
    chunks = load_relevant_chunks()
    
    # Trigger chunk processing runs and wait for completion
    run_ids = trigger_chunk_processing(chunks, snapshot_id)
    
    # Aggregate results from all runs
    results = aggregate_results(run_ids)
    
    return results


# Define the chunk processing pipeline that will be triggered
@step
def process_chunk(chunk_id: Optional[str] = None) -> dict:
    """Process a single chunk of data."""
    # Simulate chunk processing
    print(f"Processing chunk: {chunk_id}")
    return {
        "chunk_id": chunk_id,
        "processed_items": 100,
        "status": "completed"
    }


@pipeline
def chunk_processing_pipeline():
    """Pipeline that processes a single chunk."""
    result = process_chunk()
    return result


# Usage example
if __name__ == "__main__":
    # First, create a snapshot for the chunk processing pipeline
    #  This would typically be done once during setup.
    #  Make sure a remote stack is set before running this
    snapshot = chunk_processing_pipeline.create_snapshot(
        name="chunk_processing",
        description="Snapshot for processing individual chunks"
    )

    # Run the fan-out/fan-in pipeline with the snapshot
    #  You can also get the snapshot ID from the dashboard
    fan_out_fan_in_pipeline(snapshot_id=snapshot.id)
```

This pattern enables dynamic scaling, true parallelism, and database-driven workflows. Key advantages include fault tolerance and separate monitoring for each chunk. Consider resource management and proper error handling when implementing.

### Custom Step Invocation IDs

When calling a ZenML step as part of your pipeline, it gets assigned a unique **invocation ID** that you can use to reference this step invocation when defining the execution order of your pipeline steps or use it to fetch information about the invocation after the pipeline has finished running.

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

It's important to note that **retries happen at the step level, not the pipeline level**. This means that ZenML will only retry individual failed steps, not the entire pipeline.

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
def success_hook():
    print(f"Step completed successfully")

def failure_hook(exception: BaseException):
    print(f"Step failed with error: {str(exception)}")

@step(on_success=success_hook, on_failure=failure_hook)
def my_step():
    return 42
```

The following conventions apply to hooks:

* the success hook takes no arguments
* the failure hook optionally takes a single `BaseException` typed argument

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

You can use the [Alerter stack component](https://docs.zenml.io/component-guide/alerters) to send notifications when steps fail or succeed:

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
- [YAML Configuration](./yaml_configuration.md) - YAML configuration 
