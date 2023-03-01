---
description: How to run failure and success hooks after step execution
---

# Hooks

In order to perform an action after a step has completed execution,
one can leverage hooks. A hook executes right after step execution,
within the same environment as the step, therefore it has access to all the
dependencies that a step has.

Currently, there are two sorts of hooks that can be defined:

* `on_failure`: This hook triggers in event of a step failing.
* `on_success`: This hook triggers in event of a step succeeding.

A hook can be defined as a callback function, and must be accessible
within the repository where the pipeline and steps are located:

```python
def on_failure():
    print("Step failed!")

def on_success():
    print("Step succeeded!")

@step(on_failure=on_failure)
def my_failing_step() -> Output(first_num=int):
    """Returns an integer."""
    raise ValueError("Error")

@step(on_success=on_success)
def my_successful_step() -> Output(first_num=int):
    """Returns an integer."""
    raise ValueError("Error")
```

## Defining steps on a pipeline level

In some cases, there is a need to define a hook on all steps
of a given pipeline. Rather than having to define it on all
steps individually, you can also specify any hook on the pipeline
level.

Note, that step-level defined hooks take precendence over pipeline-level
defined hooks.

```python
@pipeline(on_failure=on_failure, on_success=on_success)
def my_pipeline(...):
    ...
```

## Accessing step information inside a hook

A hook function signature can optionally take three type annotated arguments of
the following types:

- `StepContext`: You can pass an object inside a hook of type `StepContext` to
get access to information such as pipeline name, run name, step name etc
- `BaseParameters`: You can pass a `BaseParemeters` inside the step
- `Exception`: In case of failure hooks, if you add an `Exception` argument to the hook,
then ZenML passes the Exception that caused your step to fail.

Please note that in case of `BaseParameters` and `Exception` the concrete class
defined by the step will be passed. For example, if a step's parameters class is
called `MyParameters`, that will be the object that is passed into the hook. Also,
if a `ValueError` is raised inside a step, the exception would also be of type
`Exception`.

```python
from zenml.steps import BaseParameters, StepContext, step

# Use one or any of these in the signature
def on_failure(context: StepContext, params: BaseParameters, exception: Exception):
    print(context.step_name)  # Output will be `my_step`
    print(type(params))  # Of type MyParameters
    print(type(exception))  # Of type value error
    print("Step failed!")


class MyParameters(BaseParameters):
    a: int = 1

@step(on_failure=on_failure)
def my_step(params: MyParameters)
    raise ValueError("My exception")
```

## Linking to the `Alerter` Stack component

A common use-case is to use the [Alerter](../../component-gallery/alerters/alerters.md)
component inside the failure or success hooks to notify relevant
people. It is quite easy to do this:

```python
def on_failure(context: StepContext):
    context.active_stack.alerter.post(
        f"{context.step_name} just failed!"
    )
```

For convenience, ZenML offers standard failure and success hooks that you can use in your
pipelines, that utilize any alerter that you have configured in your stack.

```python
from zenml.hooks import alerter_success_hook, alerter_failure_hook

@step(on_failure=alerter_failure_hook, on_success=alerter_success_hook)
def my_step(...):
    ...
```