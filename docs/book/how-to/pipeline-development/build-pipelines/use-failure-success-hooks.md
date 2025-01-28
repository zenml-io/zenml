---
description: Running failure and success hooks after step execution.
---

# Use failure/success hooks

Hooks are a way to perform an action after a step has completed execution. They can be useful in a variety of scenarios, such as sending notifications, logging, or cleaning up resources after a step has been completed.

A hook executes right after step execution, within the same environment as the step, therefore it has access to all the dependencies that a step has. Currently, there are two sorts of hooks that can be defined: `on_failure` and `on_success` .

* `on_failure`: This hook triggers in the event of a step failing.
* `on_success`: This hook triggers in the event of a step succeeding.

Here is a short demo for hooks in ZenML:

{% embed url="https://www.youtube.com/watch?v=KUW2G3EsqF8" %}
Failure and Success Hooks in ZenML Short Demo
{% endembed %}

## Defining hooks

A hook can be defined as a callback function, and must be accessible within the repository where the pipeline and steps are located.

In case of failure hooks, you can optionally add a `BaseException` argument to the hook, allowing you to access the concrete Exception that caused your step to fail:

```python
from zenml import step

def on_failure(exception: BaseException):
    print(f"Step failed: {str(exception)}")


def on_success():
    print("Step succeeded!")


@step(on_failure=on_failure)
def my_failing_step() -> int:
    """Returns an integer."""
    raise ValueError("Error")


@step(on_success=on_success)
def my_successful_step() -> int:
    """Returns an integer."""
    return 1
```

In this example, we define two hooks: `on_failure` and `on_success`, which print a message when the step fails or succeeds, respectively. We then use these hooks with two steps, `my_failing_step` and `my_successful_step`. When `my_failing_step` is executed, it raises a `ValueError`, which triggers the `on_failure` hook. Similarly, when `my_successful_step` is executed, it returns an integer successfully, which triggers the on\_success hook.

A step can also be specified as a local user-defined function path (of the form `mymodule.myfile.my_function`). This is particularly useful when defining the hooks via a [YAML Config](../../pipeline-development/use-configuration-files/).

## Defining hooks on a pipeline level

In some cases, there is a need to define a hook on all steps of a given pipeline. Rather than having to define it on all steps individually, you can also specify any hook on the pipeline level.

```python
@pipeline(on_failure=on_failure, on_success=on_success)
def my_pipeline(...):
    ...
```

{% hint style="info" %}
Note, that **step-level** defined hooks take **precedence** over **pipeline-level** defined hooks.
{% endhint %}

<details>

<summary>See it in action with the E2E example</summary>

_To set up the local environment used below, follow the recommendations from the_ [_Project templates_](../../project-setup-and-management/setting-up-a-project-repository/using-project-templates.md)_._

In [`steps/alerts/notify_on.py`](../../../../examples/e2e/steps/alerts/notify_on.py), you will find a step to notify the user about success and a function used to notify the user about step failure using the [Alerter](../../../component-guide/alerters/alerters.md) from the active stack.

We use `@step` for success notification to only notify the user about a fully successful pipeline run and not about every successful step.

In [`pipelines/training.py`](../../../../examples/e2e/pipelines/training.py), you can find the usage of a notification step and a function. We will attach a `notify_on_failure` function directly to the pipeline definition like this:

```python
from zenml import pipeline
@pipeline(
    ...
    on_failure=notify_on_failure,
    ...
)
```

At the very end of the training pipeline, we will execute the `notify_on_success` step, but only after all other steps have finished - we control it with `after` statement as follows:

```python
...
last_step_name = "promote_metric_compare_promoter"

notify_on_success(after=[last_step_name])
...
```

</details>

## Accessing step information inside a hook

Similar as for regular ZenML steps, you can use the [StepContext](../../model-management-metrics/track-metrics-metadata/fetch-metadata-within-steps.md) to access information about the current pipeline run or step inside your hook function:

```python
from zenml import step, get_step_context

def on_failure(exception: BaseException):
    context = get_step_context()
    print(context.step_run.name)  # Output will be `my_step`
    print(context.step_run.config.parameters)  # Print parameters of the step
    print(type(exception))  # Of type value error
    print("Step failed!")


@step(on_failure=on_failure)
def my_step(some_parameter: int = 1)
    raise ValueError("My exception")
```

<details>

<summary>See it in action with the E2E example</summary>

_To set up the local environment used below, follow the recommendations from the_ [_Project templates_](../../project-setup-and-management/setting-up-a-project-repository/using-project-templates.md)_._

In [`steps/alerts/notify_on.py`](../../../../examples/e2e/steps/alerts/notify_on.py), you will find a step to notify the user about success and a function used to notify the user about step failure using the [Alerter](../../../component-guide/alerters/alerters.md) from the active stack.

We use `@step` for success notification to only notify the user about a fully successful pipeline run and not about every successful step.

Inside the helper function `build_message()`, you will find an example on how developers can work with [StepContext](../../model-management-metrics/track-metrics-metadata/fetch-metadata-within-steps.md) to form a proper notification:

```python
from zenml import get_step_context

def build_message(status: str) -> str:
    """Builds a message to post.

    Args:
        status: Status to be set in text.

    Returns:
        str: Prepared message.
    """
    step_context = get_step_context()
    run_url = get_run_url(step_context.pipeline_run)

    return (
        f"Pipeline `{step_context.pipeline.name}` [{str(step_context.pipeline.id)}] {status}!\n"
        f"Run `{step_context.pipeline_run.name}` [{str(step_context.pipeline_run.id)}]\n"
        f"URL: {run_url}"
    )

@step(enable_cache=False)
def notify_on_success() -> None:
    """Notifies user on pipeline success."""
    step_context = get_step_context()
    if alerter and step_context.pipeline_run.config.extra["notify_on_success"]:
        alerter.post(message=build_message(status="succeeded"))
```

</details>

## Linking to the `Alerter` Stack component

A common use case is to use the [Alerter](../../../component-guide/alerters/alerters.md) component inside the failure or success hooks to notify relevant people. It is quite easy to do this:

```python
from zenml import get_step_context
from zenml.client import Client

def on_failure():
    step_name = get_step_context().step_run.name
    Client().active_stack.alerter.post(f"{step_name} just failed!")
```

ZenML provides standard failure and success hooks that use the alerter you have configured in your stack. Here's an example of how to use them in your pipelines:

```python
from zenml.hooks import alerter_success_hook, alerter_failure_hook


@step(on_failure=alerter_failure_hook, on_success=alerter_success_hook)
def my_step(...):
    ...
```

<details>

<summary>See it in action with the E2E example</summary>

_To set up the local environment used below, follow the recommendations from the_ [_Project templates_](../../project-setup-and-management/setting-up-a-project-repository/using-project-templates.md)_._

In [`steps/alerts/notify_on.py`](../../../../examples/e2e/steps/alerts/notify_on.py), you will find a step to notify the user about success and a function used to notify the user about step failure using the [Alerter](../../../component-guide/alerters/alerters.md) from the active stack.

We use `@step` for success notification to only notify the user about a fully successful pipeline run and not about every successful step.

Inside this code file, you can find how developers can work with Al component to send notification messages across configured channels:

```python
from zenml.client import Client
from zenml import get_step_context

alerter = Client().active_stack.alerter

def notify_on_failure() -> None:
    """Notifies user on step failure. Used in Hook."""
    step_context = get_step_context()
    if alerter and step_context.pipeline_run.config.extra["notify_on_failure"]:
        alerter.post(message=build_message(status="failed"))
```

If the Al component is not present in Stack we suppress notification, but you can also dump it to the log as Error using:

```python
from zenml.client import Client
from zenml.logger import get_logger
from zenml import get_step_context

logger = get_logger(__name__)
alerter = Client().active_stack.alerter

def notify_on_failure() -> None:
    """Notifies user on step failure. Used in Hook."""
    step_context = get_step_context()
    if step_context.pipeline_run.config.extra["notify_on_failure"]:
        if alerter:
            alerter.post(message=build_message(status="failed"))
        else:
            logger.error(message=build_message(status="failed"))
```

</details>

## Using the OpenAI ChatGPT failure hook

The OpenAI ChatGPT failure hook is a hook that uses the OpenAI integration to generate a possible fix for whatever exception caused the step to fail. It is quite easy to use. (You will need [a valid OpenAI API key](https://help.openai.com/en/articles/4936850-where-do-i-find-my-secret-api-key) that has correctly set up billing for this.)

{% hint style="warning" %}
Note that using this integration will incur charges on your OpenAI account.
{% endhint %}

First, ensure that you have the OpenAI integration installed and have stored your API key within a ZenML secret:

```shell
zenml integration install openai
zenml secret create openai --api_key=<YOUR_API_KEY>
```

Then, you can use the hook in your pipeline:

```python
from zenml.integration.openai.hooks import openai_chatgpt_alerter_failure_hook
from zenml import step

@step(on_failure=openai_chatgpt_alerter_failure_hook)
def my_step(...):
    ...
```

If you had set up a Slack alerter as your alerter, for example, then you would see a message like this:

![OpenAI ChatGPT Failure Hook](../../../.gitbook/assets/failure\_alerter.png)

You can use the suggestions as input that can help you fix whatever is going wrong in your code. If you have GPT-4 enabled for your account, you can use the `openai_gpt4_alerter_failure_hook` hook instead (imported from the same module).

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
