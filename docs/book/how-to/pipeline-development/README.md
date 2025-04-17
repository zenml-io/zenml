---
icon: paintbrush-pencil
---

# Pipeline Development

This section covers all aspects of pipeline development in ZenML.

## Iterating Over Pipeline Steps Before Execution

ZenML does not provide a direct API for iterating over steps before execution, so manual management of steps is necessary. This can be useful for scenarios such as dynamic step modification or pre-execution validation.

Here's an example of how you can manually manage steps in a list and iterate over them before running the pipeline:

```python
from zenml import pipeline, step

@step
def step_one() -> str:
    return "Step one completed."

@step
def step_two() -> str:
    return "Step two completed."

@pipeline
def my_pipeline():
    steps = [step_one, step_two]
    for step_func in steps:
        result = step_func()
        print(result)

# Define the pipeline
pipeline_instance = my_pipeline

# Loop through the steps before running
for step_func in pipeline_instance.__closure__[0].cell_contents:
    print(f"Preparing to run: {step_func.__name__}")

# Run the pipeline
pipeline_instance()
```

This code manually manages the steps in a list and iterates over them before running the pipeline. Potential use cases for this feature include dynamic step modification or pre-execution validation.