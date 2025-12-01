---
description: Write dynamic pipelines
---

# Dynamic Pipelines (Experimental)

{% hint style="warning" %}
**Experimental Feature**: Dynamic pipelines are currently an experimental feature. There are known issues and limitations, and the interface is subject to change. This feature is only supported by the `local`, `kubernetes`, `sagemaker` and `vertex` orchestrators. If you encounter any issues or have feedback, please let us know at [https://github.com/zenml-io/zenml/issues](https://github.com/zenml-io/zenml/issues).
{% endhint %}

{% hint style="info" %}
**Important**: Before using dynamic pipelines, please review the [Limitations and Known Issues](#limitations-and-known-issues) section below. This section contains critical information about requirements and known bugs that may affect your pipeline execution, especially when running remotely.
{% endhint %}

## Why Dynamic Pipelines?

Traditional ZenML pipelines require you to define the entire DAG structure at pipeline definition time. While this works well for many use cases, there are scenarios where you need more flexibility:

- **Runtime-dependent workflows**: When the number of steps or their configuration depends on data computed during pipeline execution
- **Dynamic parallelization**: When you need to spawn multiple parallel step executions based on runtime conditions
- **Conditional execution**: When the workflow structure needs to adapt based on intermediate results

Dynamic pipelines allow you to write pipelines that generate their DAG structure dynamically at runtime, giving you the power of Python's control flow (loops, conditionals) combined with ZenML's orchestration capabilities.

## Basic Example

The simplest dynamic pipeline uses regular Python control flow to determine step execution:

```python
from zenml import step, pipeline

@step
def generate_int() -> int:
    return 3

@step
def do_something(index: int) -> None:
    print(f"Processing index {index}")

@pipeline(dynamic=True)
def dynamic_pipeline() -> None:
    count = generate_int()
    # `count` is an artifact, we now load the data
    count_data = count.load()

    for idx in range(count_data):
        # This will run sequentially, like regular Python code would.
        do_something(idx)

if __name__ == "__main__":
    dynamic_pipeline()
```

In this example, the number of `do_something` steps executed depends on the value returned by `generate_int()`, which is only known at runtime.

## Key Features

### Dynamic Step Configuration

You can configure steps dynamically within your pipeline using `with_options()`:

```python
@pipeline(dynamic=True)
def dynamic_pipeline():
    some_step.with_options(enable_cache=False)()
```

This allows you to modify step behavior based on runtime conditions or data.

### Step Runtime Configuration

You can control where a step executes by specifying its runtime:

- **`runtime="inline"`**: The step runs in the orchestration environment (same process/container as the orchestrator)
- **`runtime="isolated"`**: The orchestrator spins up a separate step execution environment (new container/process)

```python
@step(runtime="isolated")
def some_step() -> None:
    # This step will run in its own isolated environment
    ...

@step(runtime="inline")
def another_step() -> None:
    # This step will run in the orchestration environment
    ...
```

Use `runtime="isolated"` when you need:
- Better resource isolation
- Different environment requirements
- Parallel execution (see below)

Use `runtime="inline"` when you need:
- Faster execution (no container startup overhead)
- Shared resources with the orchestrator
- Sequential execution

### Map/Reduce over collections

Dynamic pipelines support a high-level map/reduce pattern over sequence-like step outputs. This lets you fan out a step across items of a collection and then reduce the results without manually writing loops or loading data in the orchestration environment.

```python
from zenml import pipeline, step

@step
def producer() -> list[int]:
    return [1, 2, 3]

@step
def worker(value: int) -> int:
    return value * 2

@step
def reducer(values: list[int]) -> int:
    return sum(values)

@pipeline(dynamic=True, enable_cache=False)
def map_reduce():
    values = producer()
    results = worker.map(values)   # fan out over collection
    reducer(results)               # pass list of artifacts directly
```

Key points:
- `step.map(...)` fans out a step over sequence-like inputs.
- Steps can accept lists of artifacts directly as inputs (useful for reducers).
- You can pass the mapped output directly to a downstream step without loading in the orchestration environment.

#### Mapping semantics: map vs product

- `step.map(...)`: If multiple sequence-like inputs are provided, all must have the same length `n`. ZenML creates `n` mapped steps where the i-th step receives the i-th element from each input.
- `step.product(...)`: Creates a mapped step for each combination of elements across all input sequences (cartesian product).

Example (cartesian product):

```python
from zenml import pipeline, step

@step
def int_values() -> list[int]:
    return [1, 2]

@step
def str_values() -> list[str]:
    return ["a", "b", "c"]

@step
def do_something(a: int, b: str) -> int:
    ...

@pipeline(dynamic=True)
def cartesian_example():
    a = int_values()
    b = str_values()
    # Produces 2 * 3 = 6 mapped steps
    combine.product(a, b)
```

#### Broadcasting inputs with unmapped(...)

If you want to pass a sequence-like artifact as a whole to each mapped invocation (i.e., avoid splitting), wrap it with `unmapped(...)`:

```python
from zenml import pipeline, step, unmapped

@step
def producer(length: int) -> list[int]:
    return [1] * length

@step
def consumer(a: int, b: list[int]) -> None:
    # `b` is the full list for every mapped call
    ...

@pipeline(dynamic=True)
def unmapped_example():
    a = producer(length=3)   # list of 3 ints
    b = producer(length=4)   # list of 4 ints
    consumer.map(a=a, b=unmapped(b))
```

### Parallel Step Execution

Dynamic pipelines support true parallel execution using `step.submit()`. This method returns a `StepRunFuture` that you can use to wait for results or pass to downstream steps:

```python
from zenml import step, pipeline

@step
def some_step(arg: int) -> int:
    return arg * 2

@pipeline(dynamic=True)
def dynamic_pipeline():
    # Submit a step for parallel execution
    future = some_step.submit(arg=1)
    
    # Wait and get artifact response(s)
    artifact = future.result()
    
    # Wait and load artifact data
    data = future.load()
    
    # Pass the output to another step
    downstream_step(future)

    # Run multiple steps in parallel
    for idx in range(3):
        some_step.submit(arg=idx)
```

The `StepRunFuture` object provides several methods:

- **`result()`**: Wait for the step to complete and return the artifact response(s)
- **`load()`**: Wait for the step to complete and load the actual artifact data
- **Pass directly**: You can pass a `StepRunFuture` directly to downstream steps, and ZenML will automatically wait for it

{% hint style="info" %}
When using `step.submit()`, steps with `runtime="isolated"` will execute in separate containers/processes, while steps with `runtime="inline"` will execute in separate threads within the orchestration environment.
{% endhint %}

### Config Templates with `depends_on`

You can use YAML configuration files to provide default parameters for steps using the `depends_on` parameter:

```yaml
# config.yaml
steps:
  some_step:
    parameters:
      arg: 3
```

```python
# run.py
from zenml import step, pipeline

@step
def some_step(arg: int) -> None:
    print(f"arg is {arg}")

@pipeline(dynamic=True, depends_on=[some_step])
def dynamic_pipeline():
    some_step()

if __name__ == "__main__":
    dynamic_pipeline.with_options(config_path="config.yaml")()
```

The `depends_on` parameter tells ZenML which steps can be configured via the YAML file. This is particularly useful when you want to allow users to configure pipeline behavior without modifying code.

### Pass pipeline parameters when running snapshots from the server

When running a snapshot from the server (either via the UI or the SDK/Rest API), you can now pass pipeline parameters for your dynamic pipelines.

For example:
```python
from zenml.client import Client

Client().trigger_pipeline(snapshot_id=<ID>, run_configuration={"parameters": {"my_param": 3}})
```

## Limitations and Known Issues

### Logging

Our logging storage isn't threadsafe yet, which means logs from parallel steps may be mixed up when multiple steps execute concurrently. This is a known limitation that we're working to address.

### Error Handling

When running multiple steps concurrently using `step.submit()`, a failure in one step does not automatically stop other steps. Instead, they continue executing until finished. You should implement your own error handling logic if you need coordinated failure behavior.

### Orchestrator Support

Dynamic pipelines are currently only supported by:
- `local` orchestrator
- `kubernetes` orchestrator
- `sagemaker` orchestrator
- `vertex` orchestrator

Other orchestrators will raise an error if you try to run a dynamic pipeline with them.

### Artifact Loading

When you call `.load()` on an artifact in a dynamic pipeline, it synchronously loads the data. For large artifacts or when you want to maintain parallelism, consider passing the step outputs (future or artifact) directly to downstream steps instead of loading them.

### Mapping Limitations

- Mapping is currently supported only over artifacts produced within the same pipeline run (mapping over raw data or external artifacts is not supported).
- Chunk size for mapped collection loading defaults to 1 and is not yet configurable.

## Best Practices

1. **Use `runtime="isolated"` for parallel steps**: This ensures better resource isolation and prevents interference between concurrent step executions.

2. **Handle step outputs appropriately**: If you need the data immediately, use `.load()`. If you're just passing to another step, pass the output directly.

3. **Be mindful of resource usage**: Running many steps in parallel can consume significant resources. Monitor your orchestrator's resource limits.

4. **Test incrementally**: Start with simple dynamic pipelines and gradually add complexity. Dynamic pipelines can be harder to debug than static ones.

5. **Use config templates for flexibility**: The `depends_on` feature allows you to make pipelines configurable without code changes.

## When to Use Dynamic Pipelines

Dynamic pipelines are ideal for:

- **AI agent orchestration**: Coordinating multiple autonomous agents (e.g., retrieval or reasoning agents) whose interactions or number of invocations are determined at runtime
- **Hyperparameter tuning**: Spawning multiple training runs with different configurations
- **Data processing**: Processing variable numbers of data chunks in parallel
- **Conditional workflows**: Adapting pipeline structure based on runtime data
- **Dynamic batching**: Creating batches based on available data
- **Multi-agent and collaborative AI workflows**: Building flexible, adaptive workflows where agents or LLM-driven components can be dynamically spawned, routed, or looped based on outputs, results, or user input

For most standard ML workflows, traditional static pipelines are simpler and more maintainable. Use dynamic pipelines when you specifically need runtime flexibility that static pipelines cannot provide.

