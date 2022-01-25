# Step Fixtures

Whether defining steps using the [Functional API](../guides/functional-api) or [Class-based API](../guides/class-based-api), 
there are some special parameters that can be passed into a step function, which serve different needs.

* A `StepContext` object: This object gives access to the artifact store, metadata store, materializers, and special 
integration-specific libraries.
* An object which is a subclass of `BaseStepConfig`: This object is used to pass run-time parameters to a pipeline run. It can 
be used to send parameters to a step that are not artifacts.

These special parameters are similar to [pytest fixtures](https://docs.pytest.org/en/6.2.x/fixture.html), and so we borrow that 
nomenclature for ZenML: We call them `Step Fixtures`.

`Step Fixtures` are simple to use: Simply pass a parameter in with the right type hint as follows:

## Using fixtures in Functional API

```python
@step
def my_step(
    context: StepContext,
    config: SubClassBaseStepConfig,  # subclass of `BaseStepConfig`
    artifact: str,  # all other parameters are artifacts, coming from upstream steps
):
    ...
```

## Use fixtures in Class-based API

```python
class MyStep(BaseStep):
    def entrypoint(
        self,
        context: StepContext,
        config: SubClassBaseStepConfig,  # subclass of `BaseStepConfig`
        artifact: str,  # all other parameters are artifacts, coming from upstream steps
    ):
        ...
```

Please note in both examples above that the name of the parameter can be anything, but the typehint is what is important.

## Using the `StepContext`

`StepContext` provides additional context inside a step function.  It is used to access materializers and artifact URIs inside a step function. 

You do not need to create a StepContext object yourself and pass it when creating the step, as long as you specify 
it in the signature ZenML will create the `StepContext` and automatically pass it when executing your step.

Note: When using a StepContext inside a step, ZenML disables caching for this step by default as the context provides 
access to external resources which might influence the result of your step execution. 
To enable caching anyway, explicitly enable it in the @step decorator or when initializing your custom step class.

Within a step, there are many things that you can use the `StepContext` object for. E.g.: 

```python
@enable_INTEGRATION  # can be `enable_whylogs`, `enable_mlflow` etc. 
@step
def my_step(
    context: StepContext,
):
    context.get_output_materializer()  # Returns a materializer for a given step output.
    context.get_output_artifact_uri()  # Returns the URI for a given step output.
    context.metadata_store  # Access to the [Metadata Store](https://apidocs.zenml.io/latest/api_docs/metadata_stores/)
    context.INTEGRATION  # Access to an integration, e.g. `context.whylogs`
```

For more information, check the [API reference](https://apidocs.zenml.io/latest/api_docs/steps/)

## Using the `BaseStepConfig`

Unlike `StepContext`, we cannot pass in the `BaseStepConfig` directly to a step, but config instances can actually be 
passed when creating a step. 

We first need to sub-class it:

```python
from zenml.steps import BaseStepConfig

class MyConfig(BaseStepConfig):
    param_1: int = 1
    param_2: str = "one"
    param_3: bool = True
```

Behind the scenes, this class is essentially a [pydantic BaseModel](https://pydantic-docs.helpmanual.io/usage/models/). 
Therefore, any type that [pydantic supports](https://pydantic-docs.helpmanual.io/usage/types/) is supported. 

You can then pass it in a step as follows:

```python
@step
def my_step(
    config: MyConfig,
    ...
):
    config.param_1, config.param_2, config.param_3
```

If all properties in `MyConfig` has default values, then that is already enough. If they don't all have default values, 
then one must pass the config in during pipeline run time. You can also override default values here and therefore 
dynamically parameterize your pipeline runs.

```python
@pipeline
def my_pipeline(my_step):
    ...

pipeline = my_pipeline(
    my_step=my_step(config=MyConfig(param_1=2)),
)
```
