# Imports
```python
import os

from zenml import pipeline, step
from zenml.annotations import Input, Param, Step, Output
from zenml.artifacts.data_artifacts.text_artifact import TextArtifact
```

# Starting steps..
Let's start with a basic step. In ZenML, it should be a fully-typed function, meaning all params should 
have type hints and there should be a clear output.

The params and return value can be of any primitive or Pydantic supported type.

```python
@step
def SimplestStepEver(basic_param_1: int, basic_param_2: str) -> int:  # you can also return a list of these
    return basic_param_1 + int(basic_param_2)

@step
def SimplestSecondStepEver(sum_from_above: Input[int], another_param: int) -> float:
    return sum_from_above / 4

@pipeline
def SimplePipeline(
    first_step: Step[SimplestStepEver],
    second_step: Step[SimplestSecondStepEver],
):
    second_step.set_inputs(
        sum_from_above=first_step.outputs[0]
    )

# Pipeline
split_pipeline = SimplePipeline(
    first_step=SimplestStepEver(2, '2'),  # SimplestStepEver(2, 2) will return error.
    second_step=SimplestSecondStepEver(another_param=2)
)

run = split_pipeline.run()

print(run.steps.first_step.outputs)  # should be 4
print(run.steps.second_step.outputs)  # should be 1
```

## TODO: 
* Multiple outputs for this sort of step?

# But we are dealing with non-primitive inputs and outputs.
Most of the time, the stuff passed between steps is not simply params, but also data. This is 
where annotations come into the picture.

```python
@step
def DataStep(
    basic_param_1: int,
    basic_param_2: str,
    output_data: Output[TextArtifact]   # this is an output data artifact to send to the next step
) -> int:  # you can also return like before, it wont matter.
    
    df = create_df_with_params(basic_param_1, basic_param_2)
    
    # at this point we have two options:
    writer = output_data.get_writers('pandas')
    writer.save(df)
    # or 
    writer = PandasMaterializer()
    writer.save(output_data, df)
    
    return basic_param_1 + int(basic_param_2)

@step
def SecondDataStep(
    sum_from_above: int,
    input_data: Input[TextArtifact]  # this is an input data artifact from a previous step 
) -> float:
    reader = PandasMaterializer()
    df = reader.read(input_data)
    return df[['passenger_count', 'DOLocationID']].groupby('DOLocationID').sum()


@pipeline
def SimplePipeline(
        first_step: Step[DataStep],
        second_step: Step[SecondDataStep],
):
    second_step.set_inputs(
        sum_from_above=first_step.return_outputs[0],
        input_data=first_step.data_outputs.output_data  # now we have data outputs as well
    )


# Pipeline
split_pipeline = SimplePipeline(
    step=DataStep(2, '2')  # SimplestStepEver(2, 2) will return error.
)

run = split_pipeline.run()

print(run.steps.first_step.outputs.output_data)
```


# What if the artifacts are too big to handle?


```python
@step
def DataStep(
    basic_param_1: int,
    basic_param_2: str,
    output_data: Output[TextArtifact]   # this is an output data artifact to send to the next step
) -> int:  # you can also return like before, it wont matter.
    
    df = create_df_with_params(basic_param_1, basic_param_2)
    writer = PandasMaterializer()
    writer.save(output_data, df)
    
    return basic_param_1 + int(basic_param_2)

@step
def SecondDistributedStep(
    sum_from_above: int,
    input_data: Input[TextArtifact]  # this is an input data artifact from a previous step 
) -> float:
    
    my_beam = BeamMaterializer().read()
    
    df = reader.read(input_data)
    return df[['passenger_count', 'DOLocationID']].groupby('DOLocationID').sum()


@pipeline
def SimplePipeline(
        first_step: Step[DataStep],
        second_step: Step[SecondDistributedStep],
):
    second_step.set_inputs(
        sum_from_above=first_step.return_outputs[0],
        input_data=first_step.data_outputs.output_data  # now we have data outputs as well
    )


# Pipeline
split_pipeline = SimplePipeline(
    step=DataStep(2, '2')  # SimplestStepEver(2, 2) will return error.
)

run = split_pipeline.run()

print(run.steps.first_step.outputs.output_data)
```
