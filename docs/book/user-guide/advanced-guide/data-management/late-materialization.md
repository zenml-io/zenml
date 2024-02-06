---
description: Always use up-to-date data in ZenML pipelines.
---

# Late materialization in pipelines

Often ZenML pipeline steps consume artifacts produced by one another directly in the pipeline code, but there are scenarios where you need to pull external data into your steps. Such external data could be artifacts produced by non-ZenML codes. For those cases it is advised to use [ExternalArtifact](../../../user-guide/starter-guide/manage-artifacts.md#consuming-external-artifacts-within-a-pipeline), but what if we plan to exchange data created with other ZenML pipelines?

ZenML pipelines are first compiled and only executed at some later point. During the compilation phase all function calls are executed and this data is fixed as step input parameters. Given all this, the late materialization of dynamic objects, like data artifacts, is crucial. Without late materialization it would not be possible to pass not-yet-existing artifacts as step inputs, or their metadata, which is often the case in a multi-pipeline setting.

We identify two major use cases for exchanging artifacts between pipelines:
* You semantically group your data products using [ZenML Models](model-management.md#linking-artifacts-to-models)
* You prefer to use [ZenML Client](../../../reference/python-client.md#client-methods) to bring all the pieces together

In the sections below we will dive deeper into these use cases from the pipeline perspective.

## Use ZenML Models to exchange artifacts

The ZenML Model is an entity introduced together with [the Model Control Plane](model-management.md). The Model Control Plane is how you manage your models through a unified interface. It allows you to combine the logic of your pipelines, artifacts and crucial business data along with the actual 'technical model'.

Documentation for [ZenML Models](model-management.md#linking-artifacts-to-models) describes in great detail how you can link various artifacts produced within pipelines to the model. Here we will focus more on the part that relates to consumption.

First, let's have a look at a two-pipeline project, where the first pipeline is running training logic and the second runs batch inference leveraging trained model artifact(s):

```python
from typing_extensions import Annotated
from zenml import get_pipeline_context, pipeline, Model
from zenml.enums import ModelStages
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
    model=Model(
        name="iris_classifier",
        # Using the production stage
        version=ModelStages.PRODUCTION,
    ),
)
def do_predictions():
    # model name and version are derived from pipeline context
    model = get_pipeline_context().model
    inference_data = load_data()
    predict(
        # Here, we load in the `trained_model` from a trainer step
        model=model.get_model_artifact("trained_model"),  
        data=inference_data,
    )


if __name__ == "__main__":
    do_predictions()
```

In the example above we used `get_pipeline_context().model` property to acquire the model context in which the pipeline is running. During pipeline compilation this context will not yet have been evaluated, because `Production` model version is not a stable version name and another model version can become `Production` before it comes to the actual step execution. The same applies to calls like `model.get_model_artifact("trained_model")`; it will get stored in the step configuration for delayed materialization which will only happen during the step run itself.

It is also possible to achieve the same using bare `Client` methods reworking the pipeline code as follows:

```python
from zenml.client import Client

@pipeline
def do_predictions():
    # model name and version are directly passed into client method
    model = Client().get_model_version("iris_classifier", ModelStages.PRODUCTION)
    inference_data = load_data()
    predict(
        # Here, we load in the `trained_model` from a trainer step
        model=model.get_model_artifact("trained_model"),  
        data=inference_data,
    )
```

In this case the evaluation of the actual artifact will happen only when the step is actually running.

## Use client methods to exchange artifacts

If you don't yet use the Model Control Plane you can still exchange data between pipelines with late materialization. Let's rework the `do_predictions` pipeline code once again as follows:

```python
from typing_extensions import Annotated
from zenml import get_pipeline_context, pipeline, Model
from zenml.client import Client
from zenml.enums import ModelStages
import pandas as pd
from sklearn.base import ClassifierMixin


@step
def predict(
    model1: ClassifierMixin,
    model2: ClassifierMixin,
    model1_metric: float,
    model2_metric: float,
    data: pd.DataFrame,
) -> Annotated[pd.Series, "predictions"]:
    # compare which models performs better on the fly
    if model1_metric < model2_metric:
        predictions = pd.Series(model1.predict(data))
    else:
        predictions = pd.Series(model2.predict(data))
    return predictions

@pipeline
def do_predictions():
    # get specific artifact version
    model_42 = Client().get_artifact_version("trained_model", version="42")
    metric_42 = model_42.run_metadata["MSE"].value

    # get latest artifact version
    model_latest = Client().get_artifact_version("trained_model")
    metric_latest = model_latest.run_metadata["MSE"].value

    inference_data = load_data()
    predict(
        model1=model_42,  
        model2=model_latest,
        model1_metric=metric_42,
        model2_metric=metric_latest,
        data=inference_data,
    )

if __name__ == "__main__":
    do_predictions()
```

Here we also enriched the `predict` step logic with a metric comparison by MSE metric, so predictions are done on the best possible model. As before, calls like `Client().get_artifact_version("trained_model", version="42")` or `model_latest.run_metadata["MSE"].value` are not evaluating the actual objects behind them at pipeline compilation time. Rather, they do so only at the point of step execution. By doing so we ensure that latest version is actually the latest at the moment and not just the latest at the point of pipeline compilation.

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>