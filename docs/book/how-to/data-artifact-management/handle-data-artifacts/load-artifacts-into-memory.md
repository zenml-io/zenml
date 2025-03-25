# Load artifacts into memory

Often ZenML pipeline steps consume artifacts produced by one another directly in the pipeline code, but there are scenarios where you need to pull external data into your steps. Such external data could be artifacts produced by non-ZenML codes. For those cases, it is advised to use [ExternalArtifact](https://docs.zenml.io/user-guides/starter-guide/manage-artifacts#consuming-external-artifacts-within-a-pipeline), but what if we plan to exchange data created with other ZenML pipelines?

ZenML pipelines are first compiled and only executed at some later point. During the compilation phase, all function calls are executed, and this data is fixed as step input parameters. Given all this, the late materialization of dynamic objects, like data artifacts, is crucial. Without late materialization, it would not be possible to pass not-yet-existing artifacts as step inputs, or their metadata, which is often the case in a multi-pipeline setting.

We identify two major use cases for exchanging artifacts between pipelines:

* You semantically group your data products using ZenML Models
* You prefer to use [ZenML Client](https://docs.zenml.io/reference/python-client#client-methods) to bring all the pieces together

{% hint style="warning" %}
We recommend using models to group and access artifacts across pipelines. Find out how to load an artifact from a ZenML Model [here](https://docs.zenml.io/how-to/model-management-metrics/model-control-plane/load-artifacts-from-model).
{% endhint %}

## Use client methods to exchange artifacts

If you don't yet use the Model Control Plane, you can still exchange data between pipelines with late materialization. Let's rework the `do_predictions` pipeline code as follows:

```python
from typing import Annotated
from zenml import step, pipeline
from zenml.client import Client
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
    # compare which model performs better on the fly
    if model1_metric < model2_metric:
        predictions = pd.Series(model1.predict(data))
    else:
        predictions = pd.Series(model2.predict(data))
    return predictions

@step
def load_data() -> pd.DataFrame:
    # load inference data
    ...

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

Here, we enriched the `predict` step logic with a metric comparison by MSE metric, so predictions are done on the best possible model. We also added a `load_data` step to load the inference data.

As before, calls like `Client().get_artifact_version("trained_model", version="42")` or `model_latest.run_metadata["MSE"].value` are not evaluating the actual objects behind them at pipeline compilation time. Rather, they do so only at the point of step execution. By doing so, we ensure that the latest version is actually the latest at the moment and not just the latest at the point of pipeline compilation.

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
