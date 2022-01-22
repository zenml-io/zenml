# Step Fixtures

Whether defining steps using the [Functional API](../guides/functional-api) or [Class-based API](../guides/class-based-api), 
there are some special parameters that can be passed into a step function.

* An object which is a subclass of `BaseParameterClass`.
* A `StepContext` object.

These special parameters are similar to [pytest fixtures](https://docs.pytest.org/en/6.2.x/fixture.html).

## Functional API

```python


@step
def my_step(
    context: StepContext,
    config: ,
    artifact: str,  # all other parameters are artifacts, coming from upstream steps
):
    ...
```

## High Level API

```python


class MyStep(BaseStep):
    def entrypoint(
        self,
        context: StepContext,
        config: ,
        artifact: str,  # all other parameters are artifacts, coming from upstream steps
    ):
        ...
```

## Using the `BaseParameterClass`

## Using the `StepContext`