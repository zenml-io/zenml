---
description: Managing steps in ZenML.
---

# Managing steps in ZenML

We have learned a lot about [step configurations](configure-steps-pipelines.md) in the last section. Here we go into even further detail on how to manage steps and their configuration in ZenML.

## Type annotations

Your functions will work as ZenML steps even if you don't provide any type annotations for their inputs and outputs. However, adding type annotations to your step functions gives you lots of additional benefits:

* **Type validation of your step inputs**: ZenML makes sure that your step functions receive an object of the correct type from the upstream steps in your pipeline.
* **Better serialization**: Without type annotations, ZenML uses [Cloudpickle](https://github.com/cloudpipe/cloudpickle) to serialize your step outputs. When provided with type annotations, ZenML can choose a [materializer](../../../getting-started/core-concepts.md#materializers) that is best suited for the output. In case none of the builtin materializers work, you can even [write a custom materializer](../data-management/handle-custom-data-types.md).

{% hint style="warning" %}
ZenML provides a built-in [CloudpickleMaterializer](https://sdkdocs.zenml.io/latest/core\_code\_docs/core-materializers/#zenml.materializers.cloudpickle\_materializer.CloudpickleMaterializer) that can handle any object by saving it with [cloudpickle](https://github.com/cloudpipe/cloudpickle). However, this is not production-ready because the resulting artifacts cannot be loaded when running with a different Python version. In such cases, you should consider building a [custom Materializer](handle-custom-data-types.md#custom-materializers) to save your objects in a more robust and efficient format.

Moreover, using the `CloudpickleMaterializer` could allow users to upload of any kind of object. This could be exploited to upload a malicious file, which could execute arbitrary code on the vulnerable system.
{% endhint %}

```python
from typing import Tuple
from zenml import step

@step
def square_root(number: int) -> float:
    return number ** 0.5

# To define a step with multiple outputs, use a `Tuple` type annotation
@step
def divide(a: int, b: int) -> Tuple[int, int]:
    return a // b, a % b
```

{% hint style="info" %}
It is impossible for ZenML to detect whether you want your step to have a single output artifact of type `Tuple` or multiple output artifacts just by looking at the type annotation.

We use the following convention to differentiate between the two: When the `return` statement is followed by a tuple literal (e.g. `return 1, 2` or `return (value_1, value_2)`) we treat it as a step with multiple outputs. All other cases are treated as a step with a single output of type `Tuple`.

```python
# Single output artifact
@step
def my_step() -> Tuple[int, int]:
    output_value = (0, 1)
    return output_value

# Single output artifact with variable length
@step
def my_step(condition) -> Tuple[int, ...]:
    if condition:
        output_value = (0, 1)
    else:
        output_value = (0, 1, 2)

    return output_value

# Single output artifact using the `Annotated` annotation
@step
def my_step() -> Annotated[Tuple[int, ...], "my_output"]:
    return 0, 1


# Multiple output artifacts
@step
def my_step() -> Tuple[int, int]:
    return 0, 1


# Not allowed: Variable length tuple annotation when using
# multiple output artifacts
@step
def my_step() -> Tuple[int, ...]:
    return 0, 1
```
{% endhint %}

If you want to make sure you get all the benefits of type annotating your steps, you can set the environment variable `ZENML_ENFORCE_TYPE_ANNOTATIONS` to `True`. ZenML will then raise an exception in case one of the steps you're trying to run is missing a type annotation.

## Step output names

By default, ZenML uses the output name `output` for single output steps and `output_0, output_1, ...` for steps with multiple outputs. These output names are used to display your outputs in the dashboard and [fetch them after your pipeline is finished](../../starter-guide/fetching-pipelines.md).

If you want to use custom output names for your steps, use the `Annotated` type annotation:

```python
from typing_extensions import Annotated  # or `from typing import Annotated on Python 3.9+
from typing import Tuple
from zenml import step

@step
def square_root(number: int) -> Annotated[float, "custom_output_name"]:
    return number ** 0.5

@step
def divide(a: int, b: int) -> Tuple[
    Annotated[int, "quotient"],
    Annotated[int, "remainder"]
]:
    return a // b, a % b
```

{% hint style="info" %}
If you do not give your outputs custom names, the created artifacts will be named `{pipeline_name}::{step_name}::output` or `{pipeline_name}::{step_name}::output_{i}` in the dashboard. See the [documentation on artifact versioning and configuration](../../starter-guide/manage-artifacts.md) for more information.
{% endhint %}

## Parameters for your steps

When calling a step in a pipeline, the inputs provided to the step function can either be an **artifact** or a **parameter**. An artifact represents the output of another step that was executed as part of the same pipeline and serves as a means to share data between steps. Parameters, on the other hand, are values provided explicitly when invoking a step. They are not dependent on the output of other steps and allow you to parameterize the behavior of your steps.

{% hint style="info" %}
In order to allow the configuration of your steps using a configuration file, only values that can be serialized to JSON using Pydantic can be passed as parameters. If you want to pass other non-JSON-serializable objects such as NumPy arrays to your steps, use [External Artifacts](../../starter-guide/manage-artifacts.md#passing-artifacts-to-a-downstream-pipeline) instead.
{% endhint %}

```python
@step
def my_step(input_1: int, input_2: int) -> None:
    pass


@pipeline
def my_pipeline():
    int_artifact = some_other_step()
    # We supply the value of `input_1` as an artifact and
    # `input_2` as a parameter
    my_step(input_1=int_artifact, input_2=42)
    # We could also call the step with two artifacts or two
    # parameters instead:
    # my_step(input_1=int_artifact, input_2=int_artifact)
    # my_step(input_1=1, input_2=2)
```

Parameters of steps and pipelines can also be passed in using YAML configuration files. The following configuration file and Python code can work together and give you the flexibility to update configuration only in YAML file, once needed:
```yaml
# config.yaml

# these are parameters of the pipeline
parameters:
  environment: production

steps:
  my_step:
    # these are parameters of the step `my_step`
    parameters:
      input_2: 42
```

```python
@step
def my_step(input_1: int, input_2: int) -> None:
    pass

# input `environment` will come from the configuration file
# and it is evaluated to `production`
@pipeline
def my_pipeline(environment: str):
    # We supply value of `environment` from pipeline inputs
    int_artifact = some_other_step(environment=environment)
    # We supply the value of `input_1` as an artifact and
    # `input_2` is coming from the configuration file
    my_step(input_1=int_artifact)

if __name__=="__main__":
    my_pipeline.with_options(config_paths="config.yaml")()
```
{% hint style="warning" %}
There might be conflicting settings for step or pipeline inputs, while working with YAML configuration files. Such situations happen when you define a step or a pipeline parameter in the configuration file and override it from the code later on. Don't worry - once it happens you will be informed with details and instructions how to fix.
Example of such a conflict:
```yaml
# config.yaml
parameters:
    some_param: 24

steps:
  my_step:
    parameters:
      input_2: 42
```
```python
# run.py
@step
def my_step(input_1: int, input_2: int) -> None:
    pass

@pipeline
def my_pipeline(some_param: int):
    # here an error will be raised since `input_2` is
    # `42` in config, but `43` was provided in the code
    my_step(input_1=42, input_2=43)

if __name__=="__main__":
    # here an error will be raised since `some_param` is
    # `24` in config, but `23` was provided in the code
    my_pipeline(23)
```
{% endhint %}

**Parameters and caching**

When an input is passed as a parameter, the step will only be cached if all parameter values are exactly the same as for previous executions of the step.

**Artifacts and caching**

When an artifact is used as a step function input, the step will only be cached if all the artifacts are exactly the same as for previous executions of the step. This means that if any of the upstream steps that produce the input artifacts for a step were not cached, the step itself will always be executed.

## Using a custom step invocation ID

When calling a ZenML step as part of your pipeline, it gets assigned a unique **invocation ID** that you can use to reference this step invocation when [defining the execution order](configure-steps-pipelines.md#control-the-execution-order) of your pipeline steps or use it to [fetch information](../../starter-guide/fetching-pipelines.md) about the invocation after the pipeline has finished running.

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

## Control the execution order

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
Check out the [previous section](configure-steps-pipelines.md#using-a-custom-step-invocation-id) to learn about the invocation ID and how to use a custom one for your steps.
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

## Enable or disable logs storing

By default, ZenML uses a special logging handler to capture the logs that occur during the execution of a step. These logs are stored within the respective artifact store of your stack.

```python
import logging

from zenml import step

@step 
def my_step() -> None:
    logging.warning("`Hello`")  # You can use the regular `logging` module.
    print("World.")  # You can utilize `print` statements as well. 
```

You can display the logs in the dashboard as follows:

![Displaying step logs on the dashboard](../../../.gitbook/assets/zenml\_step\_logs.png)

If you do not want to store the logs in your artifact store, you can:

1.  Disable it by using the `enable_step_logs` parameter either with your `@pipeline` or `@step` decorator:

    ```python
    from zenml import pipeline, step

    @step(enable_step_logs=False)  # disables logging for this step
    def my_step() -> None:
        ...

    @pipeline(enable_step_logs=False)  # disables logging for the entire pipeline
    def my_pipeline():
        ...
    ```
2. Disable it by using the environmental variable `ZENML_DISABLE_STEP_LOGS_STORAGE` and setting it to `true`. This environmental variable takes precedence over the parameters mentioned above.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
