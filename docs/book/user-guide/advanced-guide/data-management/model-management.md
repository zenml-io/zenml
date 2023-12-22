---
description: Managing your models with ZenML.
---

# Model management

A `Model` is simply an entity that groups pipelines, artifacts, metadata, and other crucial business data into a unified entity. Please note that one of the most common artifacts that is associated with a Model in ZenML is the so-called technical model, which is the actualy model file/files that holds the weight and parameters of a machine learning training result. However, this is not the only artifact that is relevant; artifacts such as the training data and the predictions this model produces in production are also linked inside a ZenML Model. In this sense, a ZenML Model is a concept that more broadly encapsulates your ML products business logic.

Models are a first-class citizen in ZenML and as such
viewing and using them is unified and centralized in the ZenML API, client as
well as on the [ZenML Cloud](https://zenml.io/cloud) dashboard.

A Model captures lineage information and more. Within a Model, different Model
Versions can be staged. For example, you can rely on your predictions at a
specific stage, like `Production`, and decide whether the Model Version should
be promoted based on your business rules during training. Plus, accessing data
from other Models and their Versions is just as simple.

The Model Control Plane is how you manage your models through this unified
interface. It allows you to combine the logic of your pipelines, artifacts and
crucial business data along with the actual 'technical model'.

## Model Versions

ZenML is already versioning your models and storing some metadata, but the Model
Control Plane allows you more flexibility in terms of how you refer to and use
the models. Moreover, you can now also associate them with stages and promote
them to production, e.g. based on your business rules during training. You also
have an interface that allows you to link these versions with non-technical
artifacts and data, e.g. business data, datasets, or even stages in your process
and workflow.

## Registering models

Registering models can be done in a number of ways depending on your specific
needs. You can explicitly register models using the CLI or the Python SDK, or
you can just allow ZenML to implicitly register your models as part of a
pipeline run. (If you are using [ZenML Cloud](https://cloud.zenml.io/) you already
have access to [a dashboard interface that allows you to register
models](./model-control-plane-dashboard.md).)

### Explicit CLI registration

Registering models using the CLI is as straightforward as the following command:

```bash
zenml model register iris_logistic_regression --license=... --description=...
```

You can view some of the options of what can be passed into this command by
running `zenml model register --help` but since you are using the CLI outside a
pipeline run the arguments you can pass in are limited to non-runtime items. You
can also associate tags with models at this point, for example, using the
`--tag` option.

### Explicit dashboard registration

[ZenML Cloud](https://zenml.io/cloud) can register their models directly from
the cloud dashboard interface.

<figure><img src="../../../.gitbook/assets/mcp_model_register.png" alt="ZenML Cloud Register Model."><figcaption><p>Register a model on the [ZenML Cloud](https://zenml.io/cloud) dashboard</p></figcaption></figure>

### Explicit Python SDK registration

You can register a model using the Python SDK as follows:

```python
from zenml.models import ModelVersion
from zenml import Client

Client().create_model(
    name="iris_logistic_regression",
    license="Copyright (c) ZenML GmbH 2023",
    description="Logistic regression model trained on the Iris dataset.",
    tags=["regression", "sklearn", "iris"],
)
```

### Implicit registration by ZenML

The most common use case for registering models is to do so implicitly as part
of a pipeline run. This is done by specifying a `ModelVersion` object as part of
the `model_version` argument of the `@pipeline` decorator.

As an example, here we have a training pipeline which orchestrates the training
of a model object, storing datasets and the model object itself as links within
a newly created Model Version. This integration is achieved by configuring the
pipeline within a Model Context using `ModelVersion`. The name and
`create_new_model_version` fields are specified, while other fields remain optional for this task.

```python
from zenml import pipeline
from zenml.model import ModelVersion

@pipeline(
    enable_cache=False,
    model_version=ModelVersion(
        name="demo",
        license="Apache",
        description="Show case Model Control Plane.",
    ),
)
def train_and_promote_model():
    ...
```

Running the training pipeline creates a model and a Model Version, all while
maintaining a connection to the artifacts.

## Model versions

Each model can have many model versions. Model versions are a way for you to
track different iterations of your training process, complete with some extra
dashboard and API functionality to support the full ML lifecycle.

### When are model versions created?

Model versions are created implicitly as you are running your machine learning
training, so you don't have to immediately think about this. If you want more
control over how and when these versions are controlled, our API has you
covered, with options for whether new model versions are created as well as for
the deletion of new model versions when pipeline runs fail. [See
above](model-management.md#explicit-python-sdk-registration) for how to create
model versions explicitly.

### Explicitly name your model version

If you want to explicitly name your model version, you can do so by passing in
the `version` argument to the `ModelVersion` object. If you don't do this, ZenML
will automatically generate a version number for you.

```python
from zenml.model import ModelVersion

model_version = ModelVersion(
    name="my_model",
    version="1.0.5"
)

# The step configuration will take precedence over the pipeline
@step(model_version=model_version)
def svc_trainer(...) -> ...:
    ...

# This configures it for all steps within the pipeline
@pipeline(model_version=model_version)
def training_pipeline( ... ):
    # training happens here
```

Here we are specifically setting the model version for a particular step or for
the pipeline as a whole.

### Autonumbering of versions

ZenML automatically numbers your model versions for you. If you don't specify a version number, or if you pass `None` into the `version`
argument of the `ModelVersion` object, ZenML will automatically generate a
version number (or a new version, if you already have a version) for you. For
example if we had a model version `really_good_version` for model `my_model` and
we wanted to create a new version of this model, we could do so as follows:

```python
from zenml import ModelVersion, step

model_version = ModelVersion(
    name="my_model",
    version="even_better_version"
)

@step(model_version=model_version)
def svc_trainer(...) -> ...:
    ...
```

A new model version will be created and ZenML will track that this is the next
in the iteration sequence of the models using the `number` property. If
`really_good_version` was the 5th version of `my_model`, then
`even_better_version` will be the 6th version of `my_model`.

```python
earlier_version = ModelVersion(
    name="my_model",
    version="really_good_version"
).number # == 5

updated_version = ModelVersion(
    name="my_model",
    version="even_better_version"
).number # == 6
```

## Stages and Promotion

Model stages are a way to model the progress that a model version takes through various
stages in its lifecycle. A ZenML Model Version can be promoted to a different
stage through the Dashboard, the ZenML CLI or code.

This is a way to signify the progression of your model version through the ML
lifecycle and are an extra layer of metadata to identify the state of a
particular model version. Possible options for stages are:

- `staging`: This version is staged for production.
- `production`: This version is running in a production setting.
- `latest`: The latest version of the model. This is a virtual stage to retrieve the latest model version only - model versions cannot be promoted to `latest`.
- `archived`: This is archived and no longer relevant. This stage occurs when a
  model moves out of any other stage.

Your own particular business or use case logic will determine which model
version you choose to promote, and you can do this in the following ways:

### Promotion via CLI

This is probably the least common way that you'll use, but it's still possible
and perhaps might be useful for some use cases or within a CI system, for
example. You simply use the following CLI subcommand:

```bash
zenml model version update iris_logistic_regression --stage=...
```

### Promotion via Cloud Dashboard

This feature is not yet available, but soon you will be able to promote your
model versions directly from the ZenML Cloud dashboard. You can learn more about
this feature [here](./model-control-plane-dashboard.md).

### Promotion via Python SDK

This is the most common way that you'll use to promote your model versions. You
can see how you would do this here:

```python
from zenml import Client

MODEL_NAME = "iris_logistic_regression"
from zenml.enum import ModelStages

model_version = ModelVersion(name=MODEL_NAME, version="1.2.3")
model_version.set_stage(stage=ModelStages.PRODUCTION)

# get Latest Model Version and set it as Staging
# (if there is current Staging version it will get Archived)
latest_model_version = ModelVersion(name=MODEL_NAME, version=ModelStages.LATEST)
latest_model_version.set_stage(stage=ModelStages.STAGING)
```

Within a pipeline context, you would get the model version from the step context
but the mechanism for setting the stage is the same.

```python
from zenml import get_step_context, step, pipeline
from zenml.enums import ModelStages

@step
def promote_to_staging():
    model_version = get_step_context().model_version
    model_version.set_stage(ModelStages.STAGING, force=True)

@pipeline(
    ...
)
def train_and_promote_model():
    ...
    promote_to_staging(after=["train_and_evaluate"])
```

## Linking Artifacts to Models

Artifacts generated during pipeline runs can be linked to models and specific model versions in ZenML. This connecting of artifacts provides lineage tracking and transparency into what data and models are used during training, evaluation, and inference.

There are a few ways to link artifacts:

### Configuring the Model

The easiest way is to configure the `model_version` parameter on the `@pipeline` decorator or `@step` decorator:

```python
from zenml.model import ModelVersion 

model_version = ModelVersion(
    name="my_model",
    version="1.0.0"
)

@pipeline(model_version=model_version)
def my_pipeline():
    ...
```

This will automatically link all artifacts from this pipeline run to the
specified model version.

### Artifact Configuration

You can also explicitly specify the linkage on a per-artifact basis by passing
special configuration to the Annotated output:

```python
from zenml import ArtifactConfig

@step
def my_step() -> Annotated[MyArtifact, ArtifactConfig(model_name="my_model",
                                                      name="my_artifact",
                                                      is_model_artifact=True)]:
    ...
```

The `ArtifactConfig` object allows configuring model linkage directly on the
artifact, and you specify whether it's for a model or deployment by using the
`is_model_artifact` and `is_deployment_artifact` flags (as shown above) else it
will be assumed to be a data artifact.

### Manual Linkage

Finally, artifacts can be linked to an existing model version manually using the
SDK:

```python
model_version = ModelVersion(name="my_model", version="1.0.0")
model_version.link_artifact(my_artifact, name="new_artifact")
```

The `link_artifact` method handles creating this connection.

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
