---
description: Structuring an MLOps project
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Passing artifacts between pipelines

An MLOps project can often be broken down into many different pipelines. For example:

* A feature engineering pipeline that prepares raw data into a format ready to get trained.
* A training pipeline that takes input data from a feature engineering pipeline and trains a models on it.
* An inference pipeline that runs batch predictions on the trained model and often takes pre-processing from the training pipeline.
* A deployment pipeline that deploys a trained model into a production endpoint.

The lines between these pipelines can often get blurry: Some use cases call for these pipelines to be merged into one big pipeline. Others go further and break the pipeline down into even smaller chunks. Ultimately, the decision of how to structure your pipelines depends on the use case and requirements of the project.

No matter how you design these pipelines, one thing stays consistent: you will often need to transfer or share information (in particular artifacts, models, and metadata) between pipelines. Here are some common patterns that you can use to help facilitate such an exchange:

## Pattern 1: Artifact exchange between pipelines through `Client`

Let's say we have a feature engineering pipeline and a training pipeline. The feature engineering pipeline is like a factory, pumping out many different datasets. Only a few of these datasets should be selected to be sent to the training pipeline to train an actual model.

<figure><img src="../../.gitbook/assets/artifact_exchange.png" alt=""><figcaption><p>A simple artifact exchange between two pipelines</p></figcaption></figure>

In this scenario, the [ZenML Client](../../../reference/python-client.md#client-methods) can be used to facilitate such an exchange:

```python
from zenml import pipeline
from zenml.client import Client

@pipeline
def feature_engineering_pipeline():
    dataset = load_data()
    # This returns artifacts called "iris_training_dataset" and "iris_testing_dataset"
    train_data, test_data = prepare_data()

@pipeline
def training_pipeline():
    client = Client()
    # Fetch by name alone - uses the latest version of this artifact
    train_data = client.get_artifact_version(name="iris_training_dataset")
    # For test, we want a particular version
    test_data = client.get_artifact_version(name="iris_testing_dataset", version="raw_2023")

    # We can now send these directly into ZenML steps
    sklearn_classifier = model_trainer(train_data)
    model_evaluator(model, sklearn_classifier)
```

{% hint style="info" %}
Note that in the above example, the `train_data` and `test_data` artifacts are not [materialized](artifact-versioning.md) in memory in the `@pipeline` function, but rather the `train_data` and `test_data` objects are simply references to where this data is stored in the artifact store. Therefore, one cannot use any logic regarding the nature of this data itself during compilation time (i.e. in the `@pipeline` function).
{% endhint %}

## Pattern 2: Artifact exchange between pipelines through a `Model`

While passing around artifacts with IDs or names is very useful, it is often desirable to have the ZenML Model be the point of reference instead.

For example, let's say we have a training pipeline called `train_and_promote` and an inference pipeline called `do_predictions`. The training pipeline produces many different model artifacts, all of which are collected within a [ZenML Model](../../../user-guide/starter-guide/track-ml-models.md). Each time the `train_and_promote` pipeline runs, it creates a new `iris_classifier`. However, it only promotes the model to `production` if a certain accuracy threshold is met. The promotion can be also be done manually with human intervention, or it can be automated through setting a particular threshold.

On the other side, the `do_predictions` pipeline simply picks up the latest promoted model and runs batch inference on it. It need not know of the IDs or names of any of the artifacts produced by the training pipeline's many runs. This way these two pipelines can independently be run, but can rely on each other's output.

<figure><img src="../../.gitbook/assets/mcp_pipeline_overview.png" alt=""><figcaption><p>A simple artifact exchange between pipelines through the Model Control Plane.</p></figcaption></figure>

In code, this is very simple. Once the [pipelines are configured to use a particular model](../../../user-guide/starter-guide/track-ml-models.md#configuring-a-model-in-a-pipeline), we can use `get_step_context` to fetch the configured model within a step directly. Assuming there is a `predict` step in the `do_predictions` pipeline, we can fetch the `production` model like so:

```python
from zenml import step, get_step_context

# IMPORTANT: Cache needs to be disabled to avoid unexpected behavior
@step(enable_cache=False)
def predict(
    data: pd.DataFrame,
) -> Annotated[pd.Series, "predictions"]:
    # model name and version are derived from pipeline context
    model = get_step_context().model

    # Fetch the model directly from the model control plane
    model = model.get_model_artifact("trained_model")

    # Make predictions
    predictions = pd.Series(model.predict(data))
    return predictions
```

However, this approach has the downside that if the step is cached, then it could lead to unexpected results. You could simply disable the cache in the above step or the corresponding pipeline. However, one other way of achieving this would be to resolve the artifact at the pipeline level:

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

Ultimately, both approaches are fine. You should decide which one to use based on your own preferences.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
