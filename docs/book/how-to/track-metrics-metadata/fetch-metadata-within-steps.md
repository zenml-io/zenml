---
description: Accessing meta information in real-time within your pipeline.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Fetch metadata within steps

## Using the `StepContext`

To find information about the pipeline or step that is currently running, you can use the `zenml.get_step_context()` function to access the `StepContext` of your step:

```python
from zenml import step, get_step_context

@step
def my_step():
    step_context = get_step_context()
    pipeline_name = step_context.pipeline.name
    run_name = step_context.pipeline_run.name
    step_name = step_context.step_run.name
```

Furthermore, you can also use the `StepContext` to find out where the outputs of your current step will be stored and which [Materializer](../handle-data-artifacts/handle-custom-data-types.md) class will be used to save them:

```python
@step
def my_step():
    step_context = get_step_context()
    # Get the URI where the output will be saved.
    uri = step_context.get_output_artifact_uri()

    # Get the materializer that will be used to save the output.
    materializer = step_context.get_output_materializer() 
```

{% hint style="info" %}
See the [SDK Docs](https://sdkdocs.zenml.io/latest/core\_code\_docs/core-new/#zenml.new.steps.step\_context.StepContext) for more information on which attributes and methods the `StepContext` provides.
{% endhint %}

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
