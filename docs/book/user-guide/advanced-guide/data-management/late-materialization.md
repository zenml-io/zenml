---
description: Always use up-to-date data in ZenML pipelines.
---

# Late materialization in pipelines

Often ZenML pipeline steps consume artifacts produced by one another directly in the pipeline code, but there are scenarios where you need to pull external data into your steps. Such external data could be artifacts produced by non-ZenML codes: for those cases it is advised to use [ExternalArtifact](../../../user-guide/starter-guide/manage-artifacts.md#consuming-external-artifacts-within-a-pipeline), but what if we plan to exchange data created within other ZenML pipelines?

ZenML pipelines are first compiled and executed at later point. During compilation phase all function calls are executed and this data is fixed as step input parameters. This is way late materialization of dynamic objects, like data artifacts, is crucial. Without late materialization it would not ber possible to pass as step input not yet existing artifact or its' metadata, which is often the case in the multi pipeline setting.

We identify two major use-cases for exchange artifacts between pipelines:
* You semantically group your data products using [ZenML Models](model-management.md#linking-artifacts-to-models)
* You prefer to use [ZenML Client](../../../reference/python-client.md#client-methods) to bring all the pieces together

In the sections below we will dive deeper into these use-cases from pipelines point of view.

## Use ZenML Models to exchange artifacts

The ZenML Model is an entity introduced by The Model Control Plane feature. The Model Control Plane is how you manage your models through this unified interface. It allows you to combine the logic of your pipelines, artifacts and crucial business data along with the actual 'technical model'.

[ZenML Models documentation](model-management.md#linking-artifacts-to-models) describes in great details how you can link various artifacts produced within pipelines to the model and here we would focus more on the consumption aspect of it.

First let's have a look at the two pipeline project, where the first pipeline is running training logic and the second runs batch inference leveraging trained model artifact:

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

In the example above we used `get_pipeline_context().model` property to acquire the model context pipeline is running in. During pipeline compilation this context will be not evaluated, because `Production` model version is not stable version name and another model version can become `Production` before it comes to actual step execution. Same applies to calls like `model.get_model_artifact("trained_model")` - it will get stored in step configuration for late materialization during step run only.

It is also possible to achieve the same using bare `Client` methods reworking pipeline code as follows:

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

In this case evaluation of actual artifact will happen in delayed fashion on step run only.

## Use client methods to exchange artifacts

If you don't yet use The Model Control Plane you can still exchange data between pipelines in late materialization fashion. Let's rework `do_predictions` pipeline code once again as follows:

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

Here we also enriched `predict` step logic with metric comparison by MSE metric, so predictions are done on the best model possible. As before, calls like `Client().get_artifact_version("trained_model", version="42")` or `model_latest.run_metadata["MSE"].value` are not evaluating actual objects behind them during pipeline compilation, rather do so only in step run. By doing so we ensure that latest version is actually latest at the moment and not the latest on the pipeline compilation time.

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>