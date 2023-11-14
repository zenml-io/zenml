---
description: Managing your models with ZenML.
---

# Model management

Models are a special type of artifact that are used to represent the outputs of
a training process along with all metadata associated with that output. In other
words: models in ZenML are more broadly defined as the weights as well as any
associated information. Models are a first-class citizen in ZenML and as such
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
pipeline run. (If you are using [ZenML Cloud](https://cloud.zenml.io/) you will soon
have [a dashboard interface that allows you to register
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

The Model Control Plane interface on the dashboard is currently in testing
and will be released soon to ZenML Cloud users. Documentation for this feature
will be available [here](./model-control-plane-dashboard.md) once it is released.

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
    model_config=ModelVersion(
        name="demo",
        license="Apache",
        description="Show case Model Control Plane.",
        create_new_model_version=True,
        delete_new_version_on_failure=True,
    ),
)
def train_and_promote_model():
    ...
```

Running the training pipeline creates a model and a Model Version, all while
maintaining a connection to the artifacts.

## Model versions

### When are model versions created?

### Controlling the creation of model versions

how this is controlled by ModelConfig + solving common issues.

highlight the impossibility to run parallel pipelines "creating" same model version.

## Stages and Promotion

Model stages are a way to model the progress that a Model takes through various
stages in its lifecycle. A ZenML Model Version can be promoted to a different
stage through the Dashboard, the ZenML CLI or code.

### via CLI

```bash
zenml model version update iris_logistic_regression --stage=...
```

### via dashboard

not available yet, but you can learn more about it
[here](./model-control-plane-dashboard.md)

### via Python SDK

In the final step of the pipeline, the new Model Version is promoted to the
Staging stage.

```python
from zenml import get_step_context, step, pipeline
from zenml.enums import ModelStages

@step
def promote_to_staging():
    model_config = get_step_context().model_config
    model_version = model_config._get_model_version()
    model_version.set_stage(ModelStages.STAGING, force=True)

@pipeline(
    ...
)
def train_and_promote_model():
    ...
    promote_to_staging(after=["train_and_evaluate"])
```

```python
from zenml import Client

MODEL_NAME = "iris_logistic_regression"
from zenml.enum import ModelStages

client = Client()
# get Model by name
model = client.get_model(model_name=MODEL_NAME)

# get specific Model Version and set it as Production
# (if there is current Production version it will get Archived)
model_version = model.get_version(version="1.2.3")
model_version.set_stage(stage=ModelStages.PRODUCTION)

# get Latest Model Version and set it as Staging
# (if there is current Staging version it will get Archived)
latest_model_version = model.versions[-1]
latest_model_version.set_stage(stage=ModelStages.STAGING)
```

## Attaching metadata to artifacts

(not directly functionality of Model CP, but important thing). Now only available in same step as produced step output, but should be extended soon to attach metadata in, for example, separate evaluation step to model trained in train step.

## Reproducibility and lineage

(pointers to previous sections where you just explain which parts of the flow
would be used when you want to show provenance and how linking things together
serves this purpose)
also pointer to next page where we discuss using models

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
