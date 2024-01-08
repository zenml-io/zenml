---
description: Structuring MLOps pipelines
---

# Structuring MLOps pipelines

Now that we've learned about managing [artifacts](manage-artifacts.md) and [models](track-ml-models.md), we can shift our attention again on the thing that brings them together: [Pipelines](create-an-ml-pipeline.md).

<figure><img src="../../.gitbook/assets/mcp_pipeline_overview.png" alt=""><figcaption><p>A simple example of two pipelines interacting between each other.</p></figcaption></figure>

Each time the `train_and_promote` pipeline runs, it creates a new `iris_classifier`. However, it only promotes the created model to `production` if a certain accuracy threshold is met. The `do_predictions` pipeline simply picks up the latest promoted model and runs batch inference on it. That way these two pipelines can independently be run, but can rely on each other's output.

One way of achieving this is to fetch the model directly in your step:

```python
from zenml import step, get_step_context

# IMPORTANT: Cache needs to be disabled to avoid unexpected behavior
@step(enable_cache=False)
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

However, this approach has the downside that if the step is cached, then it could lead to unexpected results. You could simply disable the cache in the above step or the corresponding pipeline. However, one other way of achieving this would be to resolve the artifact at the pipeline level:

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

Ultimately, both approaches are fine. Users should decide which one to use based on their own preferences.

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>