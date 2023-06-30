---
description: Migrating your pipelines and steps to the new syntax.
---

# Migrate your old pipelines and steps

ZenML versions 0.40.0 to 0.41.0 introduced a new and more flexible syntax to 
define ZenML steps and pipelines. This page contains code samples that show you 
how to upgrade your steps and pipelines to the new syntax.

{% hint style="warning" %}
Newer versions of ZenML still work with pipelines and steps defined using the 
old syntax, but the old syntax is deprecated and will be removed in the future.
{% endhint %}

## Full Example

Let's look at a simplified version of the [LabelStudio Example TODO]() to get
an overview over how the pipeline and step syntax has changed.

{% tabs %}
{% tab title="Old Syntax" %}
```python
from zenml.steps import BaseParameters, Output, StepContext, step
from zenml.pipelines import pipeline


class LoadImageDataParameters(BaseParameters):
    base_path = str(
        Path(__file__).parent.absolute().parent.absolute() / "data"
    )
    dir_name = "batch_1"


@step(enable_cache=False)
def load_image_data(
    params: LoadImageDataParameters,
    context: StepContext,
) -> Output(images=Dict, uri=str):
    """Gets images from a cloud artifact store directory."""
    image_dir_path = os.path.join(params.base_path, params.dir_name)
    image_files = glob.glob(f"{image_dir_path}/*.jpeg")
    uri = context.get_output_artifact_uri("images")

    images = {}
    for i, image_file in enumerate(image_files):
        image = Image.open(image_file)
        image.load()
        artifact_filepath = (
            f"{uri}/1/{i}/{DEFAULT_IMAGE_FILENAME}.{image.format}"
        )

        images[artifact_filepath] = image

    return images, uri


class PredictionServiceLoaderParameters(BaseParameters):
    training_pipeline_name = "training_pipeline"
    training_pipeline_step_name = "model_trainer"


@step
def prediction_service_loader(
    params: PredictionServiceLoaderParameters, context: StepContext
) -> torch.nn.Module:
    train_run = get_pipeline(params.training_pipeline_name).runs[0]
    return train_run.get_step(params.training_pipeline_step_name).output.read()


@step
def predictor(
    model: torch.nn.Module, images: Dict
) -> Output(predictions=List):
    ...


@pipeline
def inference_pipeline(
    inference_data_loader,
    prediction_service_loader,
    predictor,
):
    dataset_name = get_or_create_dataset()
    new_images, new_images_uri = inference_data_loader()
    model_deployment_service = prediction_service_loader()
    preds = predictor(model_deployment_service, new_images)
    data_syncer(
        uri=new_images_uri, dataset_name=dataset_name, predictions=preds
    )


inference_pipeline(
    inference_data_loader=load_image_data(
        params=LoadImageDataParameters(
            dir_name="batch_2" if rerun else "batch_1"
        )
    ),
    prediction_service_loader=prediction_service_loader(
        PredictionServiceLoaderParameters()
    ),
    predictor=predictor(),
).run()

prediction_result = inference_pipeline.get_runs()[0].steps["predictor"].output.read()
```
{% endtab %}
{% tab title="New Syntax" %}
```python
from typing import Annotated, Any, Dict, List, Optional, Tuple

from zenml import get_step_context, pipeline, step
from zenml.client import Client


@step(enable_cache=False)
def load_image_data(
    base_path: Optional[str] = None,
    dir_name: str = "batch_1",
) -> Tuple[Annotated[Dict[str, Image.Image], "images"], Annotated[str, "uri"]]:
    """Gets images from a cloud artifact store directory."""
    if base_path is None:
        base_path = str(
            Path(__file__).parent.absolute().parent.absolute() / "data"
        )
    image_dir_path = os.path.join(base_path, dir_name)
    image_files = glob.glob(f"{image_dir_path}/*.jpeg")

    context = get_step_context()
    uri = context.get_output_artifact_uri("images")

    images = {}
    for i, image_file in enumerate(image_files):
        image = Image.open(image_file)
        image.load()
        artifact_filepath = (
            f"{uri}/1/{i}/{DEFAULT_IMAGE_FILENAME}.{image.format}"
        )

        images[artifact_filepath] = image

    return images, uri


@step
def prediction_service_loader(
    training_pipeline_name: str = "training_pipeline",
    training_pipeline_step_name: str = "pytorch_model_trainer",
) -> torch.nn.Module:
    train_run = Client().get_pipeline(training_pipeline_name).last_run
    return train_run.steps[training_pipeline_step_name].output.load()


def predictor(
    model: torch.nn.Module, images: Dict
) -> Annotated[List[Any], "predictions"]:
    ...


@pipeline
def inference_pipeline(rerun: bool = False):
    new_images, new_images_uri = load_image_data(
        dir_name="batch_2" if rerun else "batch_1"
    )
    model_deployment_service = prediction_service_loader()
    preds = predictor(model_deployment_service, new_images)


inference_pipeline(rerun=rerun)

prediction_result = inference_pipeline.last_run.steps["predictor"].output.load()
```
{% endtab %}
{% endtabs %}

## Step-by-Step Examples

## Defining steps

```python
# Old: Subclass `BaseParameters` to define parameters for a step
from zenml.steps import step, BaseParameters
from zenml.pipelines import pipeline

class MyStepParameters(BaseParameters):
    param_1: int
    param_2: Optional[float] = None

@step
def my_step(params: MyStepParameters) -> None:
    ...

@pipeline
def my_pipeline(my_step):
    my_step()

step_instance = my_step(params=MyStepParameters(param_1=17))
pipeline_instance = my_pipeline(my_step=step_instance)

# New: Directly define the parameters as arguments of your step function.
# In case you still want to group your parameters in a separate class,
# you can subclass `pydantic.BaseModel` and use that as an argument of your
# step function
from zenml import pipeline, step

@step
def my_step(param_1: int, param_2: Optional[float] = None) -> None:
    ...

@pipeline
def my_pipeline():
    my_step(param_1=17)
```

Check out [this page](./configure-steps-pipelines.md#parameters-for-your-steps)
for more information on how to parameterize your steps.

## Calling a step outside of a pipeline

```python
# Old: Call `step.entrypoint(...)`
from zenml.steps import step

def my_step() -> None:
    ...

my_step.entrypoint()

# New: Call the step directly `step(...)`
from zenml import step

def my_step() -> None:
    ...

my_step()
```

## Defining pipelines

```python
# Old: The pipeline function gets steps as inputs and calls
# the passed steps
from zenml.pipelines import pipeline

@pipeline
def my_pipeline(my_step):
    my_step()

# New: The pipeline function calls the step directly
from zenml import pipeline, step

@step
def my_step() -> None:
    ...

@pipeline
def my_pipeline():
    my_step()
```

## Configuring pipelines

```python
# Old: Create an instance of the pipeline and then call `pipeline_instance.configure(...)`
from zenml.pipelines import pipeline
from zenml.steps import step

def my_step() -> None:
    ...

@pipeline
def my_pipeline(my_step):
    my_step()

pipeline_instance = my_pipeline(my_step=my_step())
pipeline_instance.configure(enable_cache=False)

# New: Call the `with_options(...)` method on the pipeline
from zenml import pipeline, step

@step
def my_step() -> None:
    ...

@pipeline
def my_pipeline():
    my_step()

my_pipeline = my_pipeline.with_options(enable_cache=False)
```

## Running pipelines

```python
# Old: Create an instance of the pipeline and then call `pipeline_instance.run(...)`
from zenml.pipelines import pipeline
from zenml.steps import step

def my_step() -> None:
    ...

@pipeline
def my_pipeline(my_step):
    my_step()

pipeline_instance = my_pipeline(my_step=my_step())
pipeline_instance.run(...)

# New: Call the pipeline
from zenml import pipeline, step

@step
def my_step() -> None:
    ...

@pipeline
def my_pipeline():
    my_step()

my_pipeline()
```

## Scheduling pipelines

```python
# Old: Create an instance of the pipeline and then call `pipeline_instance.run(schedule=...)`
from zenml.pipelines import pipeline, Schedule
from zenml.steps import step

def my_step() -> None:
    ...

@pipeline
def my_pipeline(my_step):
    my_step()

schedule = Schedule(...)
pipeline_instance = my_pipeline(my_step=my_step())
pipeline_instance.run(schedule=schedule)

# New: Set the schedule using the `pipeline.with_options(...)` method and then run it
from zenml.pipelines import Schedule
from zenml import pipeline, step

@step
def my_step() -> None:
    ...

@pipeline
def my_pipeline():
    my_step()

schedule = Schedule(...)
my_pipeline = my_pipeline.with_options(schedule=schedule)
my_pipeline()
```

Check out [this page](./schedule-pipeline-runs.md)
for more information on how to schedule your pipelines.

## Controlling the step execution order

```python
# Old: Use the `step.after(...)` method to define upstream steps
from zenml.pipelines import pipeline

@pipeline
def my_pipeline(step_1, step_2, step_3):
    step_1()
    step_2()
    step_3()
    step_3.after(step_1)
    step_3.after(step_2)

# New: Pass the upstream steps for the `after` argument
# when calling a step
from zenml import pipeline

@pipeline
def my_pipeline():
    step_1()
    step_2()
    step_3(after=["step_1", "step_2"])
```

Check out [this page](./configure-steps-pipelines.md#control-the-execution-order)
for more information on how to control the step execution order.

## Defining steps with multiple outputs

```python
# Old: Use the `Output` class
from zenml.steps import step, Output

@step
def my_step() -> Output(int_output=int, str_output=str):
    ...

# New: Use a `Tuple` annotation and optionally assign custom output names
from typing_extensions import Annotated
from typing import Tuple
from zenml import step

# Default output names `output_0`, `output_1`
@step
def my_step() -> Tuple[int, str]:
    ...

# Custom output names
@step
def my_step() -> Tuple[
    Annotated[int, "int_output"],
    Annotated[str, "str_output"],
]:
    ...
```

Check out [this page](./configure-steps-pipelines.md#type-annotations)
for more information on how to annotate your step outputs.


<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
