---
description: How to control the order in which steps get executed
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


By default, ZenML uses the data flowing between steps of your pipeline to 
determine the order in which steps get executed. The following example
shows a pipeline in which `step_3` depends on the outputs of `step_1`
and `step_2`. This means that ZenML can execute both `step_1` and `step_2` in
parallel but needs to wait until both are finished before `step_3` can be
started.

```python
from zenml.pipelines import pipeline

@pipeline
def example_pipeline(step_1, step_2, step_3):
    step_1_output = step_1()
    step_2_output = step_2()
    step_3(step_1_output, step_2_output)
```

If you have additional constraints on the order in which steps get executed,
you can specify non-data dependencies by calling `step.after(some_other_step)`:

```python
from zenml.pipelines import pipeline

@pipeline
def example_pipeline(step_1, step_2, step_3):
    step_1.after(step_2)
    step_1_output = step_1()
    step_2_output = step_2()
    step_3(step_1_output, step_2_output)
```

This pipeline is similar to the one explained above, but this time ZenML will
make sure to only start `step_1` after `step_2` has finished.
