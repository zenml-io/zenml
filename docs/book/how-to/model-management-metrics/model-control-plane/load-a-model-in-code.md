# Load a model in code

There are a few different ways to load a ZenML Model in code:

## Load the active model in a pipeline

You can also use the [active model](../../user-guide/starter-guide/track-ml-models.md) to get the model metadata, or the associated artifacts directly as described in the [starter guide](../../user-guide/starter-guide/track-ml-models.md):

```python
from zenml import step, pipeline, get_step_context, pipeline, Model

@pipeline(model=Model(name="my_model"))
def my_pipeline():
    ...

@step
def my_step():
    # Get model from active step context
    mv = get_step_context().model

    # Get metadata
    print(mv.run_metadata["metadata_key"].value)

    # Directly fetch an artifact that is attached to the model
    output = mv.get_artifact("my_dataset", "my_version")
    output.run_metadata["accuracy"].value
```

## Load any model via the Client

Alternatively, you can use the `Client`:

```python
from zenml import step
from zenml.client import Client
from zenml.enums import ModelStages

@step
def model_evaluator_step()
    ...
    # Get staging model version 
    try:
        staging_zenml_model = Client().get_model_version(
            model_name_or_id="<INSERT_MODEL_NAME>",
            model_version_name_or_number_or_id=ModelStages.STAGING,
        )
    except KeyError:
        staging_zenml_model = None
    ...
```
<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>


