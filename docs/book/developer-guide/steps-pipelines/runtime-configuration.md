---
description: Configure Step and Pipeline Parameters for Each Run.
---

# Runtime Configuration

A ZenML pipeline clearly separates business logic from parameter configuration.
Business logic is what defines a step or a pipeline. 
Parameter configurations are used to dynamically set parameters of your steps 
and pipelines at runtime.

You can configure your pipelines at runtime in the following ways:

* [Configuring from within code](#configuring-from-within-code): 
Do this when you are quickly iterating on your code and don't want to change
your actual step code. This is useful in the development phase.
* [Configuring with YAML config files](#configuring-from-the-cli-and-a-yaml-config-file): 
Do this when you want to launch pipeline runs without modifying the code at all.
This is the recommended way for production scenarios.

## Configuring from within code

You can add a configuration to a step by creating your configuration as a
subclass of the `BaseStepConfig`. When such a config object is passed to a step,
it is not treated like other artifacts. Instead, it gets passed into the step
when the pipeline is instantiated.

```python
import numpy as np
from sklearn.base import ClassifierMixin
from sklearn.svm import SVC

from zenml.steps import step, BaseStepConfig


class SVCTrainerStepConfig(BaseStepConfig):
    """Trainer params"""
    gamma: float = 0.001


@step
def svc_trainer(
    config: SVCTrainerStepConfig,
    X_train: np.ndarray,
    y_train: np.ndarray,
) -> ClassifierMixin:
    """Train a sklearn SVC classifier."""
    model = SVC(gamma=config.gamma)
    model.fit(X_train, y_train)
    return model
```

The default value for the `gamma` parameter is set to `0.001`. However, when
the pipeline is instantiated you can override the default like this:

```python
first_pipeline_instance = first_pipeline(
    step_1=load_digits(),
    step_2=svc_trainer(SVCTrainerStepConfig(gamma=0.01)),
)

first_pipeline_instance.run()
```

{% hint style="info" %}
Behind the scenes, `BaseStepConfig` is implemented as a 
[Pydantic BaseModel](https://pydantic-docs.helpmanual.io/usage/models/).
Therefore, any type that 
[Pydantic supports](https://pydantic-docs.helpmanual.io/usage/types/)
is also supported as an attribute type in the `BaseStepConfig`.
{% endhint %}

## Configuring with YAML config files

In addition to setting parameters for your pipeline steps in code as seen above,
ZenML also allows you to use a configuration [YAML](https://yaml.org) file.

There are two ways how YAML config files can be used:
- [Defining step parameters only](#defining-step-parameters-only) and setting
the path to the config with `pipeline.with_config()` before calling
`pipeline.run()`,
- [Configuring the entire pipeline at runtime](#configuring-the-entire-pipeline-at-runtime)
and executing it with `zenml pipeline run`.

### Defining step parameters only

If you only want to configure step parameters as above, you can do so with a
minimalistic configuration YAML file, which you use to configure a pipleline
before running it using the `with_config()` method, e.g.:

```python
first_pipeline_instance = first_pipeline(
    step_1=load_digits(),
    step_2=svc_trainer(),
)

first_pipeline_instance.with_config("path_to_config.yaml").run()
```

The `path_to_config.yaml` needs to have the following structure:

```yaml
steps:
  <STEP_NAME_IN_PIPELINE>:
    parameters:
      <PARAMETER_NAME>: <PARAMETER_VALUE>
      ...
    ...
```

For our example from above, we could use the following configuration file:

```yaml
steps:
  step_2:
    parameters:
      gamma: 0.01
```

{% hint style="info" %}
Note that `svc_trainer()` still has to be defined to have a
`config: SVCTrainerStepConfig` argument. The difference here is only that we
provide `gamma` via a config file before running the pipeline, instead of
explicitly passing a `SVCTrainerStepConfig` object during the step creation.
{% endhint %}

### Configuring the entire pipeline at runtime

For production settings, you might want to use config files not only for your
parameters, but even for choosing what code gets executed.
This way, you can define entire pipeline runs without changing the code.

To run pipelines in this way, you can use the `zenml pipeline run` command with
`-c` argument:

```shell
zenml pipeline run <PATH_TO_PIPELINE_PYTHON_FILE> -c <PATH_TO_CONFIG_YAML_FILE>
```

`<PATH_TO_PIPELINE_PYTHON_FILE>` should point to the Python file where your
pipeline function or class is defined. Your steps can also be in that file,
but they do not need to. If your steps are defined in separate code files, you
can instead specify that in the YAML, as we will see [below](#defining-which-steps-to-use).

{% hint style="warning" %}
Do **not** instantiate and run your pipeline within the python file that you
want to run using the CLI, else your pipeline will be run twice, possibly with 
different configurations.
{% endhint %}

If you want to dynamically configure the entire pipeline, your config file will
need a bit more information:
- The name of the function or class of your pipeline in 
`<PATH_TO_PIPELINE_PYTHON_FILE>`,
- The name of the function or class of each step, optionally with additional
path to the the code file where it is defined (if it is not in 
`<PATH_TO_PIPELINE_PYTHON_FILE>`),
- Optionally, the name of each materializer (about which you will learn
later in the section on [Accessing Pipeline Runs](materializer.md)).

Overall, the required structure of such a YAML should look like this:

```yaml
name: <PIPELINE_CLASS_OR_FUNCTION_NAME>
steps:
  <STEP_NAME_IN_PIPELINE>:
    source:
      name: <STEP_CLASS_OR_FUNCTION_NAME>
      file: <PATH_TO_STEP_PYTHON_FILE>  # (optional)
    parameters:  # (optional)
      <PARAMETER_NAME>: <PARAMETER_VALUE>
      <SOME_OTHER_PARAMETER>: ...
    materializers:  # (optional)
      <NAME_OF_OUTPUT_OF_STEP>:
        name: <MATERIALIZER_CLASS_NAME>
        file: <PATH_TO_MATERIALIZER_PYTHON_FILE>
      <SOME_OTHER_OUTPUT>:
        ...
  <SOME_OTHER_STEP>:
    ...
```

This might seem daunting at first, so let us go over it one by one:

### Defining which pipeline to use

```yaml
name: <PIPELINE_CLASS_OR_FUNCTION_NAME>
```

The first line of the YAML defines which pipeline code to use.
In case you defined your pipeline as Python function with `@pipeline` decorator, 
this name is the name of the decorated function. 
If you used the [Class Based API](./class-based-api.md) (which you will learn 
about in the next section), it will be the name of the class.

For example, if you have defined a pipeline `my_pipeline_a` in
`pipelines/my_pipelines.py`, then you would:
- Set `name: my_pipeline_a` in the YAML,
- Use `pipelines/my_pipelines.py` as `<PATH_TO_PIPELINE_PYTHON_FILE>`.

### Defining which steps to use

For each step, you can define which source code to use via the `source` field:

```yaml
steps:
  <STEP_NAME_IN_PIPELINE>:
    source:
      name: <STEP_CLASS_OR_FUNCTION_NAME>
      file: <PATH_TO_STEP_PYTHON_FILE>  # (optional)
```

For example, if you have defined a step `my_step_1` in `steps/my_steps.py` that
you want to use as `step_1` of your pipeline `my_pipeline_a`, then you would
define that in your YAML like this:

```yaml
name: my_pipeline_a
steps:
  step_1:
    source:
      name: my_step_1
      file: steps/my_steps.py
```

If your step is defined in the same file as your pipeline, you can omit the
last `file: ...` line.

### Defining materializer source codes

The `materializers` field of a step can be used to specify custom materializers
of your step outputs and inputs.

Materializers are responsible for saving and loading artifacts within each step.
For more details on materializers and how to configure them in YAML config
files, see the [Materializers](../advanced-concepts/materializer.md#runtime-configuration.md)
section in the list of advanced concepts.

### Code Summary

Putting it all together, we can configure our entire example pipeline run like
this in the CLI:

{% tabs %}
{% tab title="CLI Command" %}

```shell
zenml pipeline run run.py -c config.yaml
```

{% endtab %}
{% tab title="run.py" %}

```python
import numpy as np
from sklearn.base import ClassifierMixin
from sklearn.svm import SVC

from zenml.integrations.sklearn.helpers.digits import get_digits
from zenml.steps import BaseStepConfig, Output, step
from zenml.pipelines import pipeline


@step
def load_digits() -> Output(
    X_train=np.ndarray, X_test=np.ndarray, y_train=np.ndarray, y_test=np.ndarray
):
    """Loads the digits dataset as normal numpy arrays."""
    X_train, X_test, y_train, y_test = get_digits()
    return X_train, X_test, y_train, y_test


class SVCTrainerStepConfig(BaseStepConfig):
    """Trainer params"""
    gamma: float = 0.001


@step
def svc_trainer(
    config: SVCTrainerStepConfig,
    X_train: np.ndarray,
    y_train: np.ndarray,
) -> ClassifierMixin:
    """Train a sklearn SVC classifier."""
    model = SVC(gamma=config.gamma)
    model.fit(X_train, y_train)
    return model


@pipeline
def first_pipeline(step_1, step_2):
    X_train, X_test, y_train, y_test = step_1()
    step_2(X_train, y_train)
```

{% endtab %}
{% tab title="config.yaml" %}

```yaml
name: first_pipeline
steps:
  step_1:
    source:
      name: load_digits
  step_2:
    source:
      name: svc_trainer
    parameters:
      gamma: 0.01
```

{% endtab %}
{% tab title="Equivalent run from python" %}
This is what the same pipeline run would look like if triggered from within python.

```python
first_pipeline_instance = first_pipeline(
    step_1=load_digits(),
    step_2=svc_trainer(SVCTrainerStepConfig(gamma=0.01)),
)

first_pipeline_instance.run()
```

{% endtab %}
{% endtabs %}

{% hint style="info" %}
Pro-Tip: You can use this to configure and run your pipeline from within
your [github action](https://docs.github.com/en/actions) (or comparable tools).
This way you ensure each run is directly associated with a code version.
{% endhint %}
