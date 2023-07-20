---
description: Accessing meta information in real-time within your pipeline.
---

# Fetch metadata within steps

### Step & run information using the `StepContext`

To find information about the pipeline or step that is currently running, you
can use the `zenml.get_step_context()` function to access the `StepContext` of
your step:

```python
from zenml import get_step_context

@step
def my_step():
    step_context = get_step_context()
    pipeline_name = step_context.pipeline.name
    run_name = step_context.pipeline_run.name
    step_name = step_context.step_run.name
```

Furthermore, you can also use the `StepContext` to find out where the outputs
of your current step will be stored and which 
[Materializer](../artifact-management/handle-custom-data-types.md) class will be used to save them:

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
See the [API Docs](https://sdkdocs.zenml.io/latest/core_code_docs/core-new/#zenml.new.steps.step_context.StepContext) for more information on which attributes and methods the `StepContext` provides.
{% endhint %}

### Fetching secret values in a step

ZenML secrets are groupings of **key-value pairs** which are securely stored in the ZenML secrets store. Additionally, a secret always has a **name** that allows you to fetch or reference them in your pipelines and stacks. In order to learn more about how to configure and create secrets, please refer to the [platform guide on secrets](../../../platform-guide/set-up-your-mlops-platform/use-the-secret-store/use-the-secret-store.md).

You can access secrets directly from within your steps through the ZenML `Client` API. This allows you to use your secrets for querying APIs from within your step without hard-coding your access keys:

```python
from zenml import step
from zenml.client import Client


@step
def secret_loader() -> None:
    """Load the example secret from the server."""
    # Fetch the secret from ZenML.
    secret = Client().get_secret(<SECRET_NAME>)

    # `secret.secret_values` will contain a dictionary with all key-value
    # pairs within your secret.
    authenticate_to_some_api(
        username=secret.secret_values["username"],
        password=secret.secret_values["password"],
    )
    ...
```

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
