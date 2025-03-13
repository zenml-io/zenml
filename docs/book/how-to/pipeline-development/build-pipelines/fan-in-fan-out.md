---
description: Running steps in parallel.
---

# Fan-in and Fan-out Patterns

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


<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
