---
description: Accessing meta information in real-time within your pipeline.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Fetch metadata within steps

### Fetching secret values in a step

ZenML secrets are groupings of **key-value pairs** which are securely stored in the ZenML secrets store. Additionally, a secret always has a **name** that allows you to fetch or reference them in your pipelines and stacks. In order to learn more about how to configure and create secrets, please refer to the [platform guide on secrets](../../platform-guide/set-up-your-mlops-platform/use-the-secret-store/use-the-secret-store.md).

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

### Step & run information using the `StepContext`

{% hint style="warning" %}
The feature of accessing step and run metadata within steps is currently under development and is expected to undergo significant changes in the upcoming releases. While it is functional at the moment, the development team is working hard to enhance its capabilities and make it more user-friendly. To stay up-to-date with the latest changes, keep in touch with us through our [Slack](https://zenml.io/slack-invite) channel and our [release notes on GitHub](https://github.com/zenml-io/zenml/releases).
{% endhint %}

Aside from artifacts and parameters, you can also pass a parameter with the type `StepContext` to the input signature of your step. This object will provide additional context inside your step function, and it will give you access to the related artifacts, parameters, materializers, and stack components directly from within the step.

```python
from zenml.steps import StepContext
from zenml import step

@step
def my_step(
    context: StepContext,  # must have the `StepContext` type annotation
    artifact: ...,
):
    ...
```

{% hint style="info" %}
The name of the argument can be anything, only the type hint is important. I.e., you don't necessarily need to call your argument `context`.
{% endhint %}

#### Defining steps with the `StepContext`

You do not need to create a `StepContext` object yourself and pass it when creating the step. As long as you specify a parameter of type `StepContext` in the signature of your step function or class, ZenML will automatically create the `StepContext` and take care of passing it to your step at runtime.

{% hint style="warning" %}
When using a `StepContext` inside a step, ZenML disables caching for this step by default as the context provides access to external resources which might influence the result of your step execution. To enable caching anyway, explicitly enable it in the `@step` decorator with `@step(enable_cache=True)` or when initializing your custom step class.
{% endhint %}

#### Using the `StepContext`

Within a step, there are many things that you can use the `StepContext` object for. For example, to access materializers, artifact locations, etc:

```python
from zenml.steps import StepContext
from zenml import step

@step
def my_step(context: StepContext):
    context.get_output_materializer()  # Get materializer for a given output.
    context.get_output_artifact_uri()  # Get URI for a given output.
```

You can also use it to get access to your stack and the actual components within your stack:

```python
from zenml.steps import StepContext
from zenml import step

@step
def my_step(context: StepContext):
    print(context.stack.artifact_store)  # Get the artifact store.
    print(context.stack.orchestrator)  # Get the orchestrator.
```

{% hint style="info" %}
See the [API Docs](https://apidocs.zenml.io/latest/core_code_docs/core-steps/#zenml.steps.step_context.StepContext) for more information on which attributes and methods the `StepContext` provides.
{% endhint %}

### Step & run information using the `Environment` class

In addition to StepContext, ZenML provides another interface where ZenML data can be accessed from within a step, the `Environment`, which can be used to get further information about the environment where the step is executed, such as the system it is running on, the Python version, the name of the current step, pipeline, and run, and more.

As an example, this is how you could use the `Environment` to find out the name of the current step, pipeline, and run:

```python
from zenml.environment import Environment


@step
def my_step(...):
    env = Environment().step_environment
    step_name = env.step_name
    pipeline_name = env.pipeline_name
    run_id = env.run_name
```

{% hint style="info" %}
In order to explore all possible operations that can be performed via the `Environment`, please consult the API docs section on [Environment](https://apidocs.zenml.io/latest/core_code_docs/core-environment/#zenml.environment.Environment).
{% endhint %}
