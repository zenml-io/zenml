---
description: Interact with Past Runs inside a Step
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To check the latest version please [visit https://docs.zenml.io](https://docs.zenml.io)
{% endhint %}


# Fetching historic runs

## The need to fetch historic runs

Sometimes, it is necessary to fetch information from previous runs in order to make a decision within a currently 
executing step. Examples of this:

* Fetch the best model evaluation results from all past pipeline runs to decide whether to deploy a newly-trained model.
* Fetching a model out of a list of trained models.
* Fetching the latest model produced by a different pipeline to run an inference on.

## Utilizing `StepContext`

ZenML allows users to fetch historical parameters and artifacts using the `StepContext` 
[fixture](./step-fixtures.md).

As an example, see this step that uses the `StepContext` to query the metadata store while running a step.
We use this to evaluate all models of past training pipeline runs and store the current best model. 
In our inference pipeline, we could then easily query the metadata store to fetch the best performing model.

```python
from zenml.steps import step, StepContext

@step
def my_third_step(context: StepContext, input_int: int) -> bool:
    """Step that decides if this pipeline run produced the highest value
    for `input_int`"""
    highest_int = 0

    # Inspect all past runs of `first_pipeline`
    try:
        pipeline_runs = (context.metadata_store
                                .get_pipeline("first_pipeline")
                                .runs)
    except KeyError:
        # If this is the first time running this pipeline you don't want
        #  it to fail
        print('No previous runs found, this run produced the highest '
              'number by default.')
        return True
    else:
        for run in pipeline_runs:
            # get the output of the second step
            try:
                multiplied_output_int = (run.get_step("step_2")
                                            .outputs['multiplied_output_int']
                                            .read())
            except KeyError:
                # If you never ran the pipeline or ran it with steps that
                #  don't produce a step with the name
                #  `multiplied_output_int` then you don't want this to fail
                pass
            else:
                if multiplied_output_int > highest_int:
                    highest_int = multiplied_output_int

    if highest_int > input_int:
        print('Previous runs produced a higher number.')
        return False  # There was a past run that produced a higher number
    else:
        print('This run produced the highest number.')
        return True  # The current run produced the highest number
```

Just like that you are able to compare runs with each other from within the run itself. 

### Summary in Code

<details>
    <summary>Code Example of this Section</summary>

```python
from random import randint
from zenml.steps import step, Output, StepContext
from zenml.pipelines import pipeline

@step
def my_first_step() -> Output(output_int=int, output_float=float):
    """Step that returns a pre-defined integer and float"""
    return 7, 0.1

@step(enable_cache=False)
def my_second_step(
        input_int: int, input_float: float
) -> Output(multiplied_output_int=int, multiplied_output_float=float):
    """Step that doubles the inputs"""
    multiplier = randint(0, 100)
    return multiplier * input_int, multiplier * input_float

@step
def my_third_step(context: StepContext, input_int: int) -> bool:
    """Step that decides if this pipeline run produced the highest value
    for `input_int`"""
    highest_int = 0

    # Inspect all past runs of `first_pipeline`
    try:
        pipeline_runs = (context.metadata_store
                                .get_pipeline("first_pipeline")
                                .runs)
    except KeyError:
        # If this is the first time running this pipeline you don't want
        #  it to fail
        print('No previous runs found, this run produced the highest '
              'number by default.')
        return True
    else:
        for run in pipeline_runs:
            # get the output of the second step
            try:
                multiplied_output_int = (run.get_step("step_2")
                                            .outputs['multiplied_output_int']
                                            .read())
            except KeyError:
                # If you never ran the pipeline or ran it with steps that
                #  don't produce a step with the name
                #  `multiplied_output_int` then you don't want this to fail
                pass
            else:
                if multiplied_output_int > highest_int:
                    highest_int = multiplied_output_int

    if highest_int > input_int:
        print('Previous runs produced a higher number.')
        return False  # There was a past run that produced a higher number
    else:
        print('This run produced the highest number.')
        return True  # The current run produced the highest number

@pipeline
def first_pipeline(
    step_1,
    step_2,
    step_3
):
    output_1, output_2 = step_1()
    output_1, output_2 = step_2(output_1, output_2)
    is_best_run = step_3(output_1)

first_pipeline(step_1=my_first_step(),
               step_2=my_second_step(),
               step_3=my_third_step()).run()
```
</details>
