# What is a step?

Conceptually, a `Step` is a discrete and independent part of a pipeline that is responsible for one particular aspect of data manipulation inside a [ZenML pipeline](../pipelines/what-is-a-pipeline.md). For example, a `SplitStep` is responsible for splitting the data into various split's like `train` and `eval` for downstream steps to then use.

A ZenML installation already comes with many `standard` steps found in `zenml.core.steps.*` for users to get started. However, it is easy and intended for users to extend these steps or even create steps from scratch as it suits their needs.

## Repository functionalities
You can get all your steps using the [Repository](../repository/what-is-a-repository.md) class:

```python
from zenml.core.repo.repo import Repository

repo: Repository = Repository.get_instance()

# Print all version stamped steps used in repository pipelines 
repo.get_step_versions()

# Get all versions of a particular step
repo.get_step_versions_by_type('module.step.MyStep')

# Get a step by the sha
sha = '63e3948300b3f5f9cf6bf42587f7ee84efbb939a'
repo.get_step_by_version('module.step.MyStep', sha)
```

## Creating custom steps
While there are many ready-to-use Standard Steps in the `zenml` package, it will be more often than not needed to create one's own 
logic while actually using ZenML.

All ZenML steps need to inherit from the `BaseStep` class found [here](https://github.com/maiot-io/zenml/blob/main/zenml/core/steps/base_step.py).

### Creating a completely custom step
A completely custom step has only one core requirement: It must call the `super().__init__(**params)` where `params` is a dict of consisting of 
all parameters that are **required to instantiate the step instance**.

```{warning}
Only use kwargs with custom step instances. Simple args are not allowed and will result in unexpected behavior.
```

### Utilizing standard Step Interfaces
While a completely custom step might be neccessary for behavior not captured in the ZenML design, more often than not, it will be 
enough to extend one of the standard step interfaces in your pipelines. These are defined as:

* DataStep interface to [create custom datasources](../datasources/what-is-a-datasource.md).
* [SplitStep](split/built-in.md) interface for custom splitting logic.
* SequencerStep interface for custom preprocessing of sequential data.
* [PreprocessStep](split/built-in.md) interface for custom preprocessing logic.
* [TrainerStep](split/built-in.md) interface for custom training logic.
* [EvaluatorStep](evaluator.md) interface for custom evaluation logic.
* [DeployerStep](deployer.md) interface for custom deployment logic.

Each StepInterface has its own functions to override and details can be found on their individual doc pages referenced above.

## Relation to TFX Components
Most standard steps are currently higher-level abstractions to [TFX components](https://github.com/tensorflow/tfx/tree/master/tfx/components), just like ZenML pipelines are higher-level abstractions of TFX pipelines.
