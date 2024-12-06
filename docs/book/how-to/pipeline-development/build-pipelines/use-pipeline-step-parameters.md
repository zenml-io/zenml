---
description: >-
  Steps and pipelines can be parameterized just like any other python function
  that you are familiar with.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Use pipeline/step parameters

## Parameters for your steps

When calling a step in a pipeline, the inputs provided to the step function can either be an **artifact** or a **parameter**. An artifact represents the output of another step that was executed as part of the same pipeline and serves as a means to share data between steps. Parameters, on the other hand, are values provided explicitly when invoking a step. They are not dependent on the output of other steps and allow you to parameterize the behavior of your steps.

{% hint style="warning" %}
In order to allow the configuration of your steps using a configuration file, only values that can be serialized to JSON using Pydantic can be passed as parameters. If you want to pass other non-JSON-serializable objects such as NumPy arrays to your steps, use [External Artifacts](../../../user-guide/starter-guide/manage-artifacts.md#consuming-external-artifacts-within-a-pipeline) instead.
{% endhint %}

```python
from zenml import step, pipeline

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
from zenml import step, pipeline
@step
def my_step(input_1: int, input_2: int) -> None:
    ...

# input `environment` will come from the configuration file,
# and it is evaluated to `production`
@pipeline
def my_pipeline(environment: str):
    ...

if __name__=="__main__":
    my_pipeline.with_options(config_paths="config.yaml")()
```

{% hint style="warning" %}
There might be conflicting settings for step or pipeline inputs, while working with YAML configuration files. Such situations happen when you define a step or a pipeline parameter in the configuration file and override it from the code later on. Don't worry - once it happens you will be informed with details and instructions how to fix. Example of such a conflict:

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
from zenml import step, pipeline

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

***

### See Also:

<table data-view="cards"><thead><tr><th></th><th></th><th></th><th data-hidden data-card-target data-type="content-ref"></th></tr></thead><tbody><tr><td>Use configuration files to set parameters</td><td></td><td></td><td><a href="use-pipeline-step-parameters.md">use-pipeline-step-parameters.md</a></td></tr><tr><td>How caching works and how to control it</td><td></td><td></td><td><a href="control-caching-behavior.md">control-caching-behavior.md</a></td></tr></tbody></table>
<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>


