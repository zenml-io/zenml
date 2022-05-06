---
description: Use Step Fixtures to Access the Stack from within a Step.
---


# Step Fixtures

In general, when defining steps, you usually can only supply inputs that have been output by previous steps.
However, there are some exceptions. 

* An object which is a subclass of `BaseStepConfig`: This object is used to pass run-time parameters to a pipeline run. 
It can be used to send parameters to a step that are not artifacts. You learned about this one already in the chapter
on [Step Configuration](#step-configuration)
* A `StepContext` object: This object gives access to the active stack, materializers, and special 
integration-specific libraries.

These special parameters are comparable to [Pytest fixtures](https://docs.pytest.org/en/6.2.x/fixture.html), hence the 
name 'Step fixtures'.

`Step fixtures` are simple to use. Simply pass a parameter in with the right type hint as follows:

### Using fixtures in the Functional API

```python
@step
def my_step(
    config: SubClassBaseStepConfig,  # subclass of `BaseStepConfig`
    context: StepContext,
    artifact: str,  # all other parameters are artifacts, coming from upstream steps
):
    ...
```

Please note that the name of the parameter can be anything, but the type hint is what is important.

### Using the `BaseStepConfig`

`BaseStepConfig` instances can be passed when creating a step. 

We first need to sub-class it:

```python
from zenml.steps import BaseStepConfig

class MyConfig(BaseStepConfig):
    param_1: int = 1
    param_2: str = "one"
    param_3: bool = True
```

Behind the scenes, this class is essentially a [Pydantic BaseModel](https://pydantic-docs.helpmanual.io/usage/models/). 
Therefore, any type that [Pydantic supports](https://pydantic-docs.helpmanual.io/usage/types/) is supported. 

You can then pass it in a step as follows:

```python
from zenml.steps import step
@step
def my_step(
    config: MyConfig,
    ...
):
    config.param_1, config.param_2, config.param_3
```

If all properties in `MyConfig` have default values, then that is already enough. If they don't all have default values, 
then one must pass the config during pipeline run time. You can also override default values here and therefore 
dynamically parameterize your pipeline runs.

```python
from zenml.pipelines import pipeline
@pipeline
def my_pipeline(my_step):
    ...

pipeline = my_pipeline(
    my_step=my_step(config=MyConfig(param_1=2)),
)
```

### Using the `StepContext`

Unlike `BaseStepConfig`, we can use the `StepContext` simply by adding it to our step function signature and ZenML will take care of passing the right thing when executing your step.

The `StepContext` provides additional context inside a step function. It can be used to access artifacts directly from 
within the step.

You do not need to create a StepContext object yourself and pass it when creating the step, as long as you specify 
it in the signature ZenML will create the `StepContext` and automatically pass it when executing your step.

{% hint style="info" %}
When using a StepContext inside a step, ZenML disables caching for this step by default as the context provides 
access to external resources which might influence the result of your step execution. 
To enable caching anyway, explicitly enable it in the @step decorator or when initializing your custom step class.
{% endhint %}

Within a step, there are many things that you can use the `StepContext` object for. For example
materializers, artifact locations, etc ...

```python
from zenml.steps import StepContext, step

@step
def my_step(
    context: StepContext,
):
    context.get_output_materializer()  # Returns a materializer for a given step output.
    context.get_output_artifact_uri()  # Returns the URI for a given step output.
    context.metadata_store  # Access to the [Metadata Store](https://apidocs.zenml.io/latest/api_docs/metadata_stores/)
```

For more information, check the [API reference](https://apidocs.zenml.io/latest/api_docs/steps/)

The next [section](#fetching-historic-runs) will directly address one important
use for the Step Context.
