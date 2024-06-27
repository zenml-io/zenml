# Linking model binaries/data to Models

Artifacts generated during pipeline runs can be linked to models in ZenML. This connecting of artifacts provides lineage tracking and transparency into what data and models are used during training, evaluation, and inference.

There are a few ways to link artifacts:

## Configuring the Model at a pipeline level

The easiest way is to configure the `model` parameter on the `@pipeline` decorator or `@step` decorator:

```python
from zenml import Model, pipeline

model = Model(
    name="my_model",
    version="1.0.0"
)

@pipeline(model=model)
def my_pipeline():
    ...
```

This will automatically link all artifacts from this pipeline run to the specified model configuration.

### Controlling artifact types and linkage

A ZenML model supports linking three types of artifacts:

* `Data artifacts`: These are the default artifacts. If nothing is specified, all artifacts are grouped under this category.
* `Model artifacts`: If there is a physical model artifact like a `.pkl` file or a model neural network weights file, it should be grouped in this category.
* `Deployment artifacts`: These artifacts are to do with artifacts related to the endpoints and deployments of the models.

You can also explicitly specify the linkage on a per-artifact basis by passing a special configuration to the Annotated output:

```python
from zenml import step, ArtifactConfig
from typing import Tuple
from typing_extensions import Annotated
import pandas as pd

@step
def svc_trainer(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    gamma: float = 0.001,
) -> Tuple[
    # This third argument marks this as a Model Artifact
    Annotated[ClassifierMixin, ArtifactConfig("trained_model", is_model_artifact=True)],
    # This third argument marks this as a Data Artifact
    Annotated[str, ArtifactConfig("deployment_uri", is_deployment_artifact=True)],
]:
    ...
```

The `ArtifactConfig` object allows configuring model linkage directly on the artifact, and you specify whether it's for a model or deployment by using the `is_model_artifact` and `is_deployment_artifact` flags (as shown above) else it will be assumed to be a data artifact.

## Saving intermediate artifacts

It is often handy to save some of your work half-way: steps like epoch-based training can be running slow, and you don't want to lose any checkpoints along the way if an error occurs. You can use the `save_artifact` utility function to save your data assets as ZenML artifacts. Moreover, if your step has the Model context configured in the `@pipeline` or `@step` decorator it will be automatically linked to it, so you can get easy access to it using the Model Control Plane features.

```python
from zenml import step, Model
from zenml.artifacts.utils import save_artifact
import pandas as pd
from typing_extensions import Annotated
from zenml.artifacts.artifact_config import ArtifactConfig

@step(model=Model(name="MyModel", version="1.2.42"))
def trainer(
    trn_dataset: pd.DataFrame,
) -> Annotated[
    ClassifierMixin, ArtifactConfig("trained_model", is_model_artifact=True)
]:  # this configuration will be applied to `model` output
    """Step running slow training."""
    ...

    for epoch in epochs:
        checkpoint = model.train(epoch)
        # this will save each checkpoint in `training_checkpoint` artifact
        # with distinct version e.g. `1.2.42_0`, `1.2.42_1`, etc.
        # Checkpoint artifacts will be linked to `MyModel` version `1.2.42`
        # implicitly.
        save_artifact(
            data=checkpoint,
            name="training_checkpoint",
            version=f"1.2.42_{epoch}",
        )

    ...

    return model
```

## Link artifacts explicitly

If you would like to link an artifact to a model not from the step context or even outside a step, you can use the `link_artifact_to_model` function. All you need is ready to link artifact and the configuration of a model.

```python
from zenml import step, Model, link_artifact_to_model, save_artifact
from zenml.client import Client


@step
def f_() -> None:
    # produce new artifact
    new_artifact = save_artifact(data="Hello, World!", name="manual_artifact")
    # and link it inside a step
    link_artifact_to_model(
        artifact_version_id=new_artifact.id,
        model=Model(name="MyModel", version="0.0.42"),
    )


# use existing artifact
existing_artifact = Client().get_artifact_version(name_id_or_prefix="existing_artifact")
# and link it even outside a step
link_artifact_to_model(
    artifact_version_id=existing_artifact.id,
    model=Model(name="MyModel", version="0.2.42"),
)
```
<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>


