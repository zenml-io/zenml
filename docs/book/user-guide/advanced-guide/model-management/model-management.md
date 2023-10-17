---
description: Managing your models with ZenML.
---

# Model management

BASIC INTRODUCTION
- how we conceive of models (what is a model in ZenML?)

unified place to combine pipelines, artifacts, crucial business data along with
the actual 'technical model'

- what is a model version + stage?

zenml is already versioning your models, but the new upgrades allow you more
flexibility in terms of how you refer to the models.
moreover, with the model control plane you can now also associate them with
stages and promote them to production, e.g. based on your business rules during training.

- what is ZenML doing behind the scenes to help with provenance etc.

zenml was already versioning things, but the model control plane gives you an
interface that makes sense with how people work with models in the real world.
it also allows you to link things together in a way that makes sense for your
business.

## Registering models

### explicit registration using CLI

```bash
zenml model register iris_logistic_regression --licence=... --description=...

zenml model list

zenml model versions list
```

### (explicit registration using the dashboard)

not available yet, but you can learn more about it [here](./model-control-plane-dashboard.md)

### explicit registration using Python SDK

```python
from zenml.models import Model
from zenml import Client

MODEL_NAME = "iris_logistic_regression"

client = Client()

model = Model(
    name=MODEL_NAME,
    license="Copyright (c) ZenML GmbH 2023",
    description="Logistic regression model trained on the iris dataset.",
    tags=["regression", "sklearn", "iris"],
)

# Register the model
client.register_model(model)

# Fetch the model
model = client.get_model(name=MODEL_NAME)
print(model.versions)  # See the last 50 versions
```

### implicit registration

how to specify a zenml model as part of a pipeline run using the ModelConfig object

as an example: The Training pipeline orchestrates the training of a model
object, storing datasets and the model object itself as links within a newly
created Model Version. This integration is achieved by configuring the pipeline
within a Model Context using ModelConfig. The name and create_new_model_version
fields are specified, while other fields remain optional for this task.

```python
from zenml import pipeline
from zenml.model import ModelConfig

@pipeline(
    enable_cache=False,
    model_config=ModelConfig(
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
Running the training pipeline creates a model and a Model Version, all while
maintaining a connection to the artifacts.

```bash
# run training pipeline: it will create a model, a 
# model version and link two datasets and one model 
# object to it, pipeline run is linked automatically
python3 train.py

# once training complete
# new model `demo` created
zenml model list

# new model version `1` created
zenml model version list demo

# list generic artifacts - train and test datasets are here
zenml model version artifacts demo 1

# list model objects - trained classifier here
zenml model version model_objects demo 1

# list deployments - none, as we didn't link any
zenml model version deployments demo 1

# list runs - training run linked
zenml model version runs demo 1
```


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
