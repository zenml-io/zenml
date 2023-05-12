---
description: Dynamically defining a pipeline at runtime.
---

# Using Dynamic Pipelines in ZenML

Dynamic pipelines in ZenML allow you to create pipelines with a configurable number of steps and splitting branches. This flexibility enables various use-cases, such as grid search-based hyperparameter tuning. In this guide, we will explain how to create and use dynamic pipelines in ZenML, using hyperparameter tuning as an example.

## Creating a Dynamic Pipeline

To create a dynamic pipeline, you need to define a pipeline class that inherits from the `DynamicPipeline` class, instead of ZenML's `BasePipeline` class. The pipeline class should have an `__init__` method to initialize the steps and a `connect` method to connect the steps together.

Here's an example of a dynamic pipeline class for hyperparameter tuning:

```python
from zenml.core.pipelines.dynamic_pipeline import DynamicPipeline

class HyperParameterTuning(DynamicPipeline):
    def __init__(
        self,
        load_data_step: Type[BaseStep],
        train_and_predict_step: Type[BaseStep],
        train_and_predict_best_model_step: Type[BaseStep],
        evaluate_step: Type[BaseStep],
        hyperparameters_conf_list: List[BaseParameters],
        **kwargs: Any,
    ) -> None:
        # Initialize the steps
        # ...

    def connect(self, **kwargs: BaseStep) -> None:
        # Connect the steps together
        # ...
```

In the `__init__` method, you should initialize all the steps based on the pipeline's constructor arguments. For example, in the `HyperParameterTuning` pipeline above, the number of steps depends on the number of elements in `hyperparameters_conf_list`. This allows you to create split_validation, train, and evaluate steps for each hyperparameter configuration. Finally, call the super constructor with all the steps required for the pipeline.

In the `connect` method, you should connect the steps together using the parameters defined in the pipeline constructor. This allows you to create a flexible pipeline without relying on a fixed step list or dictionary.

## Gathering Outputs from Multiple Steps

Dynamic pipelines often require gathering outputs from multiple steps and using them as inputs for another step. In the `HyperParameterTuning` pipeline example, the `compare_scores` step should receive the scores from all `evaluate` steps.

To enable this functionality, you can use two types of parameter classes:

1. `GatherStepsParameters`: This class defines parameters to identify a group of steps (by step name prefix or by a list of step names). In the `HyperParameterTuning` pipeline, `CompareScoreParams` inherits from `GatherStepsParameters`, so it contains both the parameters for the comparison of scores and the parameters to gather step outputs.

2. `OutputParameters`: Classes that inherit from this class define the output parameters of a step. This class implements the `gather` method, which receives a `GatherStepsParameters` object. The method gathers all the output values of the steps compatible with the `GatherStepsParameters` object and returns them as a collection of outputs of the concrete class inheriting from `OutputParameters`.

## Creating Multiple Pipeline Templates Dynamically

Once a ZenML pipeline is initialized, the pipeline class can only define pipelines with the specific step name and types in the class field `STEP_SPEC`. Therefore, the dynamic pipeline class cannot be reused for a pipeline with a different number of steps.

To create multiple hyperparameter tuning pipelines, you can use the `as_template_of` class method (implemented in the `DynamicPipeline` class). This method generates a new pipeline class that inherits from the dynamic pipeline, allowing you to define multiple pipeline templates with a different number of steps, sharing the same logic.

For example, you can create two different pipeline templates for hyperparameter tuning, both inheriting from the `HyperParameterTuning` class:

```python
HyperParameterTuning.as_template_of("iris_random_forest")(
    # ...
).run(enable_cache=False)

HyperParameterTuning.as_template_of("breast_cancer_random_forest")(
    # ...
).run(enable_cache=False)
```

These two pipeline templates have different numbers of hyperparameter configurations and use different data, but they share the same logic defined in the `HyperParameterTuning` class.

## Running the Dynamic Pipeline

To run the dynamic pipeline, you can use the following commands:

```shell
pip install "zenml[server]" scikit-learn

# Initialize ZenML repo
zenml init

# Start the ZenServer to enable dashboard access
zenml up

# Generate the pipelines and run
python run.py
```

This will install the required packages, initialize a ZenML repository, start the ZenServer for dashboard access, and run the dynamic pipeline.

In conclusion, dynamic pipelines in ZenML provide a flexible way to create and run pipelines with a configurable number of steps and splitting branches. By defining a pipeline class that inherits from the `DynamicPipeline` class and implementing the `__init__` and `connect` methods, you can create dynamic pipelines for various use-cases, such as hyperparameter tuning.