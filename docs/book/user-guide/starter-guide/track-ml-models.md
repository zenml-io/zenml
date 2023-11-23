---
description: Exploring the ZenML Model Control Plane
---

# Keeping track of ML models in ZenML

As discussed in the [Core Concepts](../../getting-started/core-concepts.md), ZenML also contains the notion of a `Model`, which consists of many `ModelVersions`. These concepts are exposed in the `Model Control Plane` (MCP for short).

![Walkthrough of ZenML Model Control Plane (Dashboard available only on ZenML Cloud)](../../.gitbook/assets/mcp_walkthrough.gif)

This feature empowers you to effortlessly group pipelines, artifacts, and crucial business data into a unified entity: a `Model`. A Model captures lineage information and more. Within a Model, different `Model Versions` can be staged. For example, you can rely on your predictions at a specific stage, like `production`, and decide whether the model version should be promoted based on your business rules during training.

These models can be viewed within ZenML:

{% tabs %}
{% tab title="OSS (CLI)" %}

`zenml model list` can be used to list of artifacts and their versions.

{% endtab %}
{% tab title="Cloud (Dashboard)" %}

The [ZenML Cloud](https://zenml.io/cloud) dashboard has additional capabilities, that include visualizing these models in the dashboard.

<figure><img src="../../.gitbook/assets/mcp_model_list.png" alt=""><figcaption><p>ZenML Model Control Plane.</p></figcaption></figure>

{% endtab %}
{% endtabs %}

## Configuring a Model and Model Version

The easiest way to use a ZenML model is to pass a model version object as part of a pipeline run. This can be done easily:

```python
from zenml import pipeline
from zenml.model import ModelVersion

@pipeline(
    model_version=ModelVersion(
        # The name uniquely identifies this model
        name="iris_classifier",
        # The version specifies the version
        # If None or an unseen version is specified, it will be created
        # Otherwise, a version will be fetched.
        version=None, 
        # Some other properties may be specified
        license="Apache 2.0",
        description="A classification model for the iris dataset.",
    ),
)
def training_pipeline(gamma: float = 0.002):
    # Now this pipeline will have the `iris_classifier` model active.
    X_train, X_test, y_train, y_test = training_data_loader()
    svc_trainer(gamma=gamma, X_train=X_train, y_train=y_train)

if __name__ == "__main__":
    training_pipeline()
```

The above will estabilish a link between all artifacts that pass through this ZenML pipeline and this model. You will be able to see all associated artifacts and pipeline runs all within one view.

{% tabs %}
{% tab title="OSS (CLI)" %}

`zenml model version list <MODEL_NAME>` can be used to list all versions of a particular model.

The following commands can be used to list the various pipeline runs associated with a model:

* `zenml model version runs <MODEL_NAME> <MODEL_VERSIONNAME>`

The following commands can be used to list the various artifacts associated with a model:

* `zenml model version data_artifacts <MODEL_NAME> <MODEL_VERSIONNAME>`
* `zenml model version model_artifacts <MODEL_NAME> <MODEL_VERSIONNAME>`
* `zenml model version endpoint_artifacts <MODEL_NAME> <MODEL_VERSIONNAME>`

{% endtab %}
{% tab title="Cloud (Dashboard)" %}

The [ZenML Cloud](https://zenml.io/cloud) dashboard has additional capabilities, that include visualizing all associated runs and artifacts for a model version:

<figure><img src="../../.gitbook/assets/mcp_model_versions_list.png" alt=""><figcaption><p>ZenML Model Versions List.</p></figcaption></figure>

{% endtab %}
{% endtabs %}

### Associating different types of artifacts with a Model

A ZenML model supports linking three types of artifacts:

* `Data artifacts`: These is the default artifacts. If nothing is specified, all artifacts are grouped under this category.
* `Model artifacts`: If there is a physical model artifact like a pickle file or a model neural network weights file, it should be grouped in this category.
* `Deployment artifacts`: These artifacts are to do with artifacts related to the endpoints and deployments of the models.

In order to tell ZenML which artifact belongs to which type, one must pass in additional configuration to your artifacts:

```python
from zenml import get_step_context, step
from zenml.model import DataArtifactConfig, ModelArtifactConfig

@step
def svc_trainer(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    gamma: float = 0.001,
) -> Tuple[
    # This third argument marks this as a Model Artifact
    Annotated[ClassifierMixin, "trained_model", ModelArtifactConfig()],
    # This third argument marks this as a Data Artifact
    Annotated[float, "training_acc", DataArtifactConfig()],
]:
    ...
```

### Using the Stages of a Model

A models versions can exist in various stages. These are meant to signify their lifecycle state:

* `staging`: This version is staged for production.
* `production`: This version is running in a production setting.
* `archived`: This is archived and no longer relevant. This stage occurs when a model moves out of any other stage.

{% tabs %}
{% tab title="Python SDK" %}
```python
from zenml.model import ModelVersion

# Get latest model version
model_version = ModelVersion(
    name="iris_classifier",
)

# Get a model from a version
model_version = ModelVersion(
    name="iris_classifier",
    version="my_version",
)

# Pass the stage into the version field
# to get the model by stage
model_version = ModelVersion(
    name="iris_classifier",
    version="staging",
)

# This will set this version to production
model_version.set_stage(stage="production", force=True)
```
{% endtab %}

{% tab title="CLI" %}
```shell
# List staging models
zenml model version list <MODEL_NAME> --stage staging 

# Update to production
zenml model version update <MODEL_NAME> <MODEL_VERSIONNAME> -s production 
```
{% endtab %}
{% tab title="Cloud (Dashboard)" %}
The [ZenML Cloud](https://zenml.io/cloud) dashboard has additional capabilities, that include easily changing the stage:

![ZenML Cloud Transition Model Stages](../../.gitbook/assets/dcp_transition_stage.gif)

{% endtab %}
{% endtabs %}

### Using a Model Version within a step

In this case, the model version will be available to all steps directly through the `StepContext`:

```python
from zenml import get_step_context, step

@step
def svc_trainer(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    gamma: float = 0.001,
) -> Tuple[
    Annotated[ClassifierMixin, "trained_model"],
    Annotated[float, "training_acc"],
]:
    # This will return the model version specified in the 
    # @pipeline decorator. In this case, the production version of 
    # the `iris_classifier` will be returned in this case.
    model_version = get_step_context().model_version
    ...

@pipeline(
    model_version=ModelVersion(
        # The name uniquely identifies this model
        name="iris_classifier",
        # Pass the stage you want to get the right model
        version="production", 
    ),
)
def training_pipeline(gamma: float = 0.002):
    # Now this pipeline will have the production `iris_classifier` model active.
    X_train, X_test, y_train, y_test = training_data_loader()
    svc_trainer(gamma=gamma, X_train=X_train, y_train=y_train)
```

## Facilitating Artifacts Exchange Between Pipelines Using MCP

A ZenML Model spans multiple pipelines, and is a key concept that brings disparate pipelines together. A simple example is illustrated below:

<figure><img src="../../.gitbook/assets/mcp_pipeline_overview.png" alt=""><figcaption><p>A simple example of two pipelines interacting between each other.</p></figcaption></figure>

Each time the `train_and_promote` pipeline runs, it creates a new `iris_classifier`. However, it only promotes the created model to `production` if a certain accuracy threshold is met. The `do_predictions` pipeline simply picks up the latest promoted model and runs batch inference on it. That way these two pipelines can independently be run, but can rely on each others output.

One way of achieving this is to fetch the model directly in your step:

```python
from zenml import step, get_step_context

@step
def predict(
    data: pd.DataFrame,
) -> Annotated[pd.Series, "predictions"]:
    # model_name and model_version derived from pipeline context
    model_version = get_step_context().model_version

    # Fetch the model directly from the model control plane
    model = model_version.get_model_artifact("trained_model")

    # Make predictions
    predictions = pd.Series(model.predict(data))
    return predictions
```

However, this approach has the downside that if the step is cached, then it could lead to unexpected results. You could simply disable the cache in the above step or corresponding pipeline. However, one other way of achieving this would be to resolve the artifact at the pipeline level:

```python
from typing_extensions import Annotated
from zenml import get_pipeline_context, pipeline, ExternalArtifact
from zenml.enums import ModelStages
from zenml.model import ModelVersion
import pandas as pd
from sklearn.base import ClassifierMixin


@step
def predict(
    model: ClassifierMixin,
    data: pd.DataFrame,
) -> Annotated[pd.Series, "predictions"]:
    predictions = pd.Series(model.predict(data))
    return predictions

@pipeline(
    enable_cache=False,
    model_config=ModelVersion(
        name="iris_classifier",
        # Using the production stage
        version=ModelStages.PRODUCTION,
    ),
)
def do_predictions():
    # model_name and model_version derived from pipeline context
    model_version = get_pipeline_context().model_version
    inference_data = load_data()
    predict(
        # Here, we load in the `trained_model` from a trainer step
        model=model_version.get_model_artifact("trained_model"),  
        data=inference_data,
    )


if __name__ == "__main__":
    do_predictions()
```

Ultimately, both approaches are fine. Users should decide which one to use based on their own preference.

## A Practical Example of using the Model Control Plane

A fully worked out practical example of using the Model Control Plane is [available here](https://github.com/zenml-io/zenml-plugins/tree/main/model_control_plane) for further reading!