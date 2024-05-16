# Promote a model

## Stages and Promotion

Model stages are a way to model the progress that different versions takes through various stages in its lifecycle. A ZenML Model version can be promoted to a different stage through the Dashboard, the ZenML CLI or code.

This is a way to signify the progression of your model version through the ML lifecycle and are an extra layer of metadata to identify the state of a particular model version. Possible options for stages are:

* `staging`: This version is staged for production.
* `production`: This version is running in a production setting.
* `latest`: The latest version of the model. This is a virtual stage to retrieve the latest version only - versions cannot be promoted to `latest`.
* `archived`: This is archived and no longer relevant. This stage occurs when a model moves out of any other stage.

Your own particular business or use case logic will determine which model version you choose to promote, and you can do this in the following ways:

### Promotion via CLI

This is probably the least common way that you'll use, but it's still possible and perhaps might be useful for some use cases or within a CI system, for example. You simply use the following CLI subcommand:

```bash
zenml model version update iris_logistic_regression --stage=...
```

### Promotion via Cloud Dashboard

This feature is not yet available, but soon you will be able to promote your model versions directly from the ZenML Cloud dashboard. You can learn more about this feature [here](../../user-guide/advanced-guide/data-management/model-control-plane-dashboard.md).

### Promotion via Python SDK

This is the most common way that you'll use to promote your models. You can see how you would do this here:

```python
from zenml import Client

MODEL_NAME = "iris_logistic_regression"
from zenml.enums import ModelStages

model = Model(name=MODEL_NAME, version="1.2.3")
model.set_stage(stage=ModelStages.PRODUCTION)

# get latest model and set it as Staging
# (if there is current Staging version it will get Archived)
latest_model = Model(name=MODEL_NAME, version=ModelStages.LATEST)
latest_model.set_stage(stage=ModelStages.STAGING)
```

Within a pipeline context, you would get the model from the step context but the mechanism for setting the stage is the same.

```python
from zenml import get_step_context, step, pipeline
from zenml.enums import ModelStages

@step
def promote_to_staging():
    model = get_step_context().model
    model.set_stage(ModelStages.STAGING, force=True)

@pipeline(
    ...
)
def train_and_promote_model():
    ...
    promote_to_staging(after=["train_and_evaluate"])
```
