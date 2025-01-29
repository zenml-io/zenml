---
description: Running steps in parallel.
---

# Fan-in and Fan-out Patterns

The fan-out/fan-in pattern is a common pipeline architecture where a single step splits into multiple parallel operations (fan-out) and then consolidates the results back into a single step (fan-in). ZenML supports this pattern through its pipeline architecture:

```python
@pipeline
def fan_out_fan_in_pipeline(parallel_count: int) -> None:
    # Initial step (source)
    input_data = load_data_step()
    
    # Fan out: Process data in parallel branches
    after = []
    for i in range(parallel_count):
        processed = process_data_step(input_data, batch_id=f"process_{i}")
        after.append(f"process_{i}")
    
    # Fan in: Combine results from all parallel branches
    combined_results = combine_results_step(..., after=after)
```

This pattern is particularly useful for parallel processing, distributed workloads, or when you need to process data through different transformations and then aggregate the results.

For example, you might want to process different chunks of data in parallel and then aggregate the results:

```python
from zenml import step, get_step_context
from zenml.client import Client

@step
def combine_results_step():
    """Fan-in step that combines results from multiple parallel processes"""
    run_name = get_step_context().pipeline_run.name
    run = Client().get_pipeline_run(run_name)

    # Fetch all results from parallel processing steps
    processed_results = {}
    for step_name, step in run.steps.items():
        if step_name.startswith("process_"):
            for output_name, output in step.outputs.items():
                if output_name == "processed_data":
                    result = output.load()
                    batch_id = step.config.parameters["batch_id"]
                    processed_results[batch_id] = result
    
    # Combine all results
    final_result = aggregate_results(processed_results)
    return final_result
```

The fan-out pattern allows for parallel processing and better resource utilization, while the fan-in pattern enables aggregation and consolidation of results. This is particularly useful for:

- Parallel data processing
- Distributed model training
- Ensemble methods
- Batch processing
- Data validation across multiple sources
- [Hyperparamter tuning](./hyper-parameter-tuning.md)

Note that when implementing the fan-in step, you'll need to use the ZenML Client to query the results from previous parallel steps, as shown in the example above, and you can't pass in the result directly.

{% hint style="warning" %}
The fan-in, fan-out method has the following limitations:

1. Steps run sequentially rather than in parallel if the underlying orchestrator does not support parallel step runs (e.g. with the local orchestrator)
2. The number of steps need to be known ahead-of-time, and ZenML does not yet support the ability to dynamically create steps on the fly.
{% endhint %}


<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
