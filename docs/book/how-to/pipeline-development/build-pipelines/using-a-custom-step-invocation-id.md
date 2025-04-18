# Using a custom step invocation ID

When calling a ZenML step as part of your pipeline, it gets assigned a unique **invocation ID** that you can use to reference this step invocation when [defining the execution order](control-execution-order-of-steps.md) of your pipeline steps or use it to [fetch information](../../../user-guide/tutorial/fetching-pipelines.md) about the invocation after the pipeline has finished running.

## Custom Step Run Naming

Setting custom names for step runs in ZenML pipelines is particularly useful for users who utilize the same step multiple times within a single pipeline and wish to assign unique identifiers to each invocation for clarity and conflict avoidance.

### Purpose

The purpose of setting custom step run names is to distinguish between multiple invocations of the same step within a pipeline, ensuring clarity and preventing conflicts.

### Code Example

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

### Note

Ensure that all custom step names are unique within the pipeline to prevent conflicts.

### Additional Resources

- [Using a custom step invocation ID](https://github.com/zenml-io/zenml/blob/main/docs/book/how-to/pipeline-development/build-pipelines/using-a-custom-step-invocation-id.md)
- [Slack Discussion](https://zenml.slack.com/archives/C01FWQ5D0TT/p1739499659.053539)

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>


