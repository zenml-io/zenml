# Control execution order of steps

By default, ZenML uses the data flowing between steps of your pipeline to determine the order in which steps get executed.

The following example shows a pipeline in which `step_3` depends on the outputs of `step_1` and `step_2`. This means that ZenML can execute both `step_1` and `step_2` in parallel but needs to wait until both are finished before `step_3` can be started.

```python
from zenml import pipeline

@pipeline
def example_pipeline():
    step_1_output = step_1()
    step_2_output = step_2()
    step_3(step_1_output, step_2_output)
```

If you have additional constraints on the order in which steps get executed, you can specify non-data dependencies by passing the invocation IDs of steps that should run before your step like this: `my_step(after="other_step")`. If you want to define multiple upstream steps, you can also pass a list for the `after` argument when calling your step: `my_step(after=["other_step", "other_step_2"])`.

{% hint style="info" %}
Check out the [documentation here](using-a-custom-step-invocation-id.md) to learn about the invocation ID and how to use a custom one for your steps.
{% endhint %}

```python
from zenml import pipeline

@pipeline
def example_pipeline():
    step_1_output = step_1(after="step_2")
    step_2_output = step_2()
    step_3(step_1_output, step_2_output)
```

This pipeline is similar to the one explained above, but this time ZenML will make sure to only start `step_1` after `step_2` has finished.
<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>


