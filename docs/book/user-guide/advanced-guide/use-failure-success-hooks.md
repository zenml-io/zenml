---
description: Running failure and success hooks after step execution.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


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
def on_failure(exception: BaseException):
    print(f"Step failed: {str(e)}")


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

A step can also be specified as a local user-defined function path (of the form `mymodule.myfile.my_function`). This is particularly useful when defining the hooks via a [YAML Config](configure-steps-pipelines.md).

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

## Accessing step information inside a hook

Similar as for regular ZenML steps, you can use the 
[StepContext](./fetch-metadata-within-steps.md) to access information about the 
current pipeline run or step inside your hook function:

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

## Linking to the `Alerter` Stack component

A common use case is to use the [Alerter](../component-guide/alerters/alerters.md) component inside the failure or success hooks to notify relevant people. It is quite easy to do this:

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


@step(on_failure=openai_chatgpt_alerter_failure_hook)
def my_step(...):
    ...
```

If you had set up a Slack alerter as your alerter, for example, then you would see a message like this:

![OpenAI ChatGPT Failure Hook](/docs/book/.gitbook/assets/failure_alerter.png)

You can use the suggestions as input that can help you fix whatever is going wrong in your code. If you have GPT-4 enabled for your account, you can use the `openai_gpt4_alerter_failure_hook` hook instead (imported from the same module).

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
