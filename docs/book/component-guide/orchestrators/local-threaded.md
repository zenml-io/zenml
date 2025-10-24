---
description: Orchestrating your pipelines to run locally with parallel execution.
---

# Local Threaded Orchestrator

The local threaded orchestrator is an [orchestrator](./) flavor that comes built-in with ZenML and runs your pipelines locally with support for parallel step execution.

### When to use it

The local threaded orchestrator extends the functionality of the local orchestrator by enabling concurrent execution of independent pipeline steps using multiple threads. This can significantly speed up pipeline execution when you have steps that can run in parallel.

You should use the local threaded orchestrator if:

* you want to run pipelines locally but take advantage of parallel execution for independent steps
* you're developing and testing pipelines and want faster iteration cycles
* you have a pipeline with multiple independent steps that don't depend on each other
* you want to simulate distributed execution behavior while developing locally

### How it works

The local threaded orchestrator analyzes your pipeline's DAG (Directed Acyclic Graph) structure and identifies steps that can run in parallel. Steps are executed concurrently when they have no dependencies on each other, while respecting the overall dependency chain.

For example, in a pipeline like this:

```
Step A (5s) \
Step B (5s) --> Step D (2s)
Step C (5s) /
```

Steps A, B, and C will run in parallel (taking ~5 seconds total), and then Step D will run after all three complete (~2 seconds more). The total execution time would be ~7 seconds instead of ~17 seconds if run sequentially.

### Configuration

The orchestrator supports configuring the maximum number of worker threads:

```python
from zenml.orchestrators import LocalThreadedOrchestratorConfig

config = LocalThreadedOrchestratorConfig(
    max_workers=4  # Number of parallel threads
)
```

The `max_workers` parameter controls how many steps can run concurrently:
- Defaults to the number of CPU cores on your machine
- Set to 2 for minimal parallelism
- Set to 4 for moderate parallelism
- Set to 8 or more for high parallelism on multi-core systems

### Execution Modes

The local threaded orchestrator supports all standard execution modes:

* **FAIL_FAST**: Stops scheduling new steps immediately when any step fails
* **STOP_ON_FAILURE**: Allows running steps to complete but doesn't schedule new ones after a failure
* **CONTINUE_ON_FAILURE**: Continues executing independent steps even if some fail

### How to deploy it

The local threaded orchestrator comes with ZenML and works without any additional setup.

### How to use it

To use the local threaded orchestrator, we can register it and use it in our active stack:

```shell
zenml orchestrator register <ORCHESTRATOR_NAME> --flavor=local_threaded

# Optionally configure max workers
zenml orchestrator register <ORCHESTRATOR_NAME> --flavor=local_threaded --max_workers=8

# Register and activate a stack with the new orchestrator
zenml stack register <STACK_NAME> -o <ORCHESTRATOR_NAME> ... --set
```

You can now run any ZenML pipeline using the local threaded orchestrator:

```shell
python file_that_runs_a_zenml_pipeline.py
```

The orchestrator will automatically identify independent steps and execute them in parallel.

### Limitations

* **Schedules are not supported**: The local threaded orchestrator does not support running pipelines on a schedule
* **Step resources are ignored**: Resource requirements specified for steps are not enforced
* **Shared memory**: All steps run in the same process and share memory, so be cautious with steps that modify global state

### When to switch to a different orchestrator

Consider switching to a different orchestrator when:

* You need to run pipelines on a schedule
* You need distributed execution across multiple machines
* You need isolation between step executions
* You need to enforce resource requirements for steps
* You're moving to production and need cloud infrastructure

For more information and a full list of configurable attributes of the local threaded orchestrator, check out the [SDK Docs](https://sdkdocs.zenml.io/latest/core_code_docs/core-orchestrators.html#zenml.orchestrators.local_threaded).
