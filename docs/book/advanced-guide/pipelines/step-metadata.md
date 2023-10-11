---
description: How to use step fixtures to access the active ZenML stack from within a step
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


Aside from artifacts and step parameters, you can also pass a parameter with 
the type `StepContext` to the input signature of your step. This object will 
provide additional context inside your step function, and it will give you 
access the related artifacts, materializers, and stack components directly 
from within the step.

```python
from zenml.steps import step, BaseParameters, StepContext


class SubClassBaseParameters(BaseParameters):
    ...


@step
def my_step(
    params: SubClassBaseParameters,  # must be subclass of `BaseParameters`
    context: StepContext,  # must be of class `StepContext`
    artifact: str,  # other parameters are assumed to be outputs of other steps
):
    ...
```

{% hint style="info" %}
The name of the argument can be anything, only the type hint is important. 
I.e., you don't necessarily need to call your `context`.
{% endhint %}

### Defining Steps with Step Contexts

Unlike `BaseParameters`, you do not need to create a `StepContext` object
yourself and pass it when creating the step. As long as you specify a parameter
of type `StepContext` in the signature of your step function or class, ZenML 
will automatically create the `StepContext` and take care of passing it to your
step at runtime.

{% hint style="info" %}
When using a `StepContext` inside a step, ZenML disables caching for this step 
by default as the context provides access to external resources which might
influence the result of your step execution. To enable caching anyway, 
explicitly enable it in the `@step` decorator with `@step(enable_cache=True)`
or when initializing your custom step class.
{% endhint %}

### Using Step Contexts

Within a step, there are many things that you can use the `StepContext` object
for. For example, to access materializers, artifact locations, etc:

```python
from zenml.steps import step, StepContext


@step
def my_step(context: StepContext):
    context.get_output_materializer()  # Get materializer for a given output.
    context.get_output_artifact_uri()  # Get URI for a given output.
```

You can also use it to get access to your stack and the actual components 
within your stack:

```python
from zenml.steps import step, StepContext


@step
def my_step(context: StepContext):
    print(context.stack.artifact_store)     # Get the artifact store.
    print(context.stack.orchestrator)       # Get the orchestrator.
```

{% hint style="info" %}
See the [API Docs](https://apidocs.zenml.io/latest/core_code_docs/core-steps/) for
more information on which attributes and methods the `StepContext` provides.
{% endhint %}

## How to access run names and other global data from within a step

In addition to [Step Fixtures](#using-step-contexts), ZenML provides another
interface where ZenML data can be accessed from within a step, the
`Environment`, which can be used to get further information about the
environment where the step is executed, such as the system it is running on,
the Python version, the name of the current step, pipeline, and run, and more.

As an example, this is how you could use the `Environment` to find out the name 
of the current step, pipeline, and run:

```
from zenml.environment import Environment


@step
def my_step(...)
    env = Environment().step_environment
    step_name = env.step_name
    pipeline_name = env.pipeline_name
    run_id = env.run_name
```

{% hint style="info" %}
To explore all possible operations that can be performed via the
`Environment`, please consult the API docs section on
[Environment](https://apidocs.zenml.io/latest/core_code_docs/core-environment/#zenml.environment.Environment).
{% endhint %}
