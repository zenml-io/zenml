---
description: Steps are individual tasks within a pipeline.
---

# Steps

Conceptually, a `Step` is a discrete and independent part of a pipeline that is responsible for one particular aspect of data manipulation inside a [ZenML pipeline](../pipelines/what-is-a-pipeline.md). 

A ZenML installation already comes with many `standard` steps found in `zenml.core.steps.*` for users to get started. For example, a `SplitStep` is responsible for splitting the data into various split's like `train` and `eval` for downstream steps to then use. However, in essence, virtually any Python function can be a ZenML step as well.

## How to create steps

```python
from zenml.steps import step

@step  # this is where the magic happens
def SimplestStepEver(basic_param_1: int, basic_param_2: str) -> int:
    return basic_param_1 + int(basic_param_2)
```

There are only a few considerations for the parameters and return types.

* All parameters passed into the signature must be [typed](https://docs.python.org/3/library/typing.html). Similarly, if you're returning something, it must be also be typed with the return operator \(`->`\)
* ZenML uses [Pydantic](https://pydantic-docs.helpmanual.io/usage/types/) for type checking and serialization under-the-hood, so all [Pydantic types](https://pydantic-docs.helpmanual.io/usage/types/) are supported \[full list available soon\].

While this is just a function with a decorator, it is not super useful. ZenML steps really get powerful when you put them together with [data artifacts](artifacts.md). Read about more of that here!

### Utilizing standard Step Interfaces \[Coming Soon\]

While a completely custom step might be necessary for behavior not captured in the ZenML design, more often than not, it will be enough to extend one of the standard step interfaces in your pipelines. These are defined as:

* DataStep interface to create custom datasources.
* SplitStep interface for custom splitting logic.
* SequencerStep interface for custom preprocessing of sequential data.
* PreprocessStep interface for custom preprocessing logic.
* TrainerStep interface for custom training logic.
* EvaluatorStep interface for custom evaluation logic.
* DeployerStep interface for custom deployment logic.

Each StepInterface has its own functions to override and details can be found on their individual doc pages referenced above \[coming soon\]

## Relation to TFX Components

Most standard steps are currently higher-level abstractions to [TFX components](https://github.com/tensorflow/tfx/tree/master/tfx/components), just like ZenML pipelines are higher-level abstractions of TFX pipelines.

