---
description: Managing MLFlow logged models and artifacts
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# MLflow Model Registry

[MLflow](https://www.mlflow.org/docs/latest/tracking.html) is a popular tool that helps you track experiments, manage models and even deploy them to different environments. ZenML already provides a [MLflow Experiment Tracker](../experiment-trackers/mlflow.md) that you can use to track your experiments, and an [MLflow Model Deployer](../model-deployers/mlflow.md) that you can use to deploy your models locally.

The MLflow model registry uses [the MLflow model registry service](https://mlflow.org/docs/latest/model-registry.html) to manage and track ML models and their artifacts and provides a user interface to browse them:

![MLflow Model Registry UI](../../.gitbook/assets/mlflow-ui-models.png)

## When would you want to use it?

You can use the MLflow model registry throughout your experimentation, QA, and production phases to manage and track machine learning model versions. It is designed to help teams collaborate on model development and deployment, and keep track of which models are being used in which environments. With the MLflow model registry, you can store and manage models, deploy them to different environments, and track their performance over time.

This is particularly useful in the following scenarios:

* If you are working on a machine learning project and want to keep track of different model versions as they are developed and deployed.
* If you need to deploy machine learning models to different environments and want to keep track of which version is being used in each environment.
* If you want to monitor and compare the performance of different model versions over time and make data-driven decisions about which models to use in production.
* If you want to simplify the process of deploying models either to a production environment or to a staging environment for testing.

## How do you deploy it?

The MLflow Experiment Tracker flavor is provided by the MLflow ZenML integration, so you need to install it on your local machine to be able to register an MLflow model registry component. Note that the MLFlow model registry requires [MLFlow Experiment Tracker](../experiment-trackers/mlflow.md) to be present in the stack.

```shell
zenml integration install mlflow -y
```

Once the MLflow integration is installed, you can register an MLflow model registry component in your stack:

```shell
zenml model-registry register mlflow_model_registry --flavor=mlflow

# Register and set a stack with the new model registry as the active stack
zenml stack register custom_stack -r mlflow_model_registry ... --set
```

{% hint style="info" %}
The MLFlow model registry will automatically use the same configuration as the MLFlow Experiment Tracker. So if you have a remote MLFlow tracking server configured in your stack, the MLFlow model registry will also use the same configuration.
{% endhint %}

{% hint style="warning" %}
Due to a [critical severity vulnerability](https://github.com/advisories/GHSA-xg73-94fp-g449) found in older versions of MLflow, we recommend using MLflow version 2.2.1 or higher.
{% endhint %}

## How do you use it?

There are different ways to use the MLflow model registry. You can use it in your ZenML pipelines with the built-in step, or you can use the ZenML CLI to register your model manually or call the model registry API within a custom step in your pipeline. The following sections show you how to use the MLflow model registry in your ZenML pipelines and with the ZenML CLI:

### Register models inside a pipeline

ZenML provides a predefined `mlflow_model_deployer_step` that you can use to register a model in the MLflow model registry which you have previously logged to MLflow:

```python
from zenml import pipeline
from zenml.integrations.mlflow.steps.mlflow_registry import (
    mlflow_register_model_step,
)

@pipeline
def mlflow_registry_training_pipeline():
    model = ...
    mlflow_register_model_step(
        model=model,
        name="tensorflow-mnist-model",
    )
```

{% hint style="warning" %}
The `mlflow_register_model_step` expects that the `model` it receives has already been logged to MLflow in a previous step. E.g., for a scikit-learn model, you would need to have used `mlflow.sklearn.autolog()` or `mlflow.sklearn.log_model(model)` in a previous step. See the [MLflow experiment tracker documentation](../experiment-trackers/mlflow.md) for more information on how to log models to MLflow from your ZenML steps.
{% endhint %}

#### List of available parameters

When using the `mlflow_register_model_step`, you can set a variety of parameters for fine-grained control over which information is logged with your model:

* `name`: The name of the model. This is a required parameter.
* `version`: version: The version of the model.
* `trained_model_name`: Name of the model artifact in MLflow.
* `model_source_uri`: The path to the model. If not provided, the model will be fetched from the MLflow tracking server via the `trained_model_name`.
* `description`: A description of the model version.
* `metadata`: A list of metadata to associate with the model version.

{% hint style="info" %}
The `model_source_uri` parameter is the path to the model within the MLflow tracking server.

If you are using a local MLflow tracking server, the path will be something like `file:///.../mlruns/667102566783201219/3973eabc151c41e6ab98baeb20c5323b/artifacts/model`.

If you are using a remote MLflow tracking server, the path will be something like `s3://.../mlruns/667102566783201219/3973eabc151c41e6ab98baeb20c5323b/artifacts/model`.

You can find the path of the model in the MLflow UI. Go to the `Artifacts` tab of the run that produced the model and click on the model. The path will be displayed in the URL:

<img src="../../../.gitbook/assets/mlflow-ui-model-uri.png" alt="Model URI in MLflow UI" data-size="original">
{% endhint %}

### Register models via the CLI

Sometimes adding a `mlflow_registry_training_pipeline` step to your pipeline might not be the best option for you, as it will register a model in the MLflow model registry every time you run the pipeline.

If you want to register your models manually, you can use the `zenml model-registry models register-version` CLI command instead:

```shell
zenml model-registry models register-version Tensorflow-model \
    --description="A new version of the tensorflow model with accuracy 98.88%" \
    -v 1 \
    --model-uri="file:///.../mlruns/667102566783201219/3973eabc151c41e6ab98baeb20c5323b/artifacts/model" \
    -m key1 value1 -m key2 value2 \
    --zenml-pipeline-name="mlflow_training_pipeline" \
    --zenml-step-name="trainer"
```

### Deploy a registered model

After you have registered a model in the MLflow model registry, you can also easily deploy it as a prediction service. Checkout the [MLflow model deployer documentation](../model-deployers/mlflow.md#deploy-from-model-registry) for more information on how to do that.

### Interact with registered models

You can also use the ZenML CLI to interact with registered models and their versions.

The `zenml model-registry models list` command will list all registered models in the model registry:

```shell
$ zenml model-registry models list

┏━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━┯━━━━━━━━━━┓
┃          NAME          │ DESCRIPTION │ METADATA ┃
┠────────────────────────┼─────────────┼──────────┨
┃ tensorflow-mnist-model │             │          ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━┷━━━━━━━━━━┛
```

To list all versions of a specific model, you can use the `zenml model-registry models list-versions REGISTERED_MODEL_NAME` command:

```shell
$ zenml model-registry models list-versions tensorflow-mnist-model
┏━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃          NAME          │ MODEL_VERSION │ VERSION_DESCRIPTION                     │ METADATA                                                                                                                                                                             ┃
┠────────────────────────┼───────────────┼─────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┨
┃ tensorflow-mnist-model │ 3             │ Run #3 of the mlflow_training_pipeline. │ {'zenml_version': '0.34.0', 'zenml_run_name': 'mlflow_training_pipeline-2023_03_01-08_09_23_672599', 'zenml_pipeline_name': 'mlflow_training_pipeline',                       ┃
┃                        │               │                                         │ 'zenml_pipeline_run_uuid': 'a5d4faae-ef70-48f2-9893-6e65d5e51e98', 'epochs': '5', 'optimizer': 'Adam', 'lr': '0.005'}     ┃
┠────────────────────────┼───────────────┼─────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┨
┃ tensorflow-mnist-model │ 2             │ Run #2 of the mlflow_training_pipeline. │ {'zenml_version': '0.34.0', 'zenml_run_name': 'mlflow_training_pipeline-2023_03_01-08_09_08_467212', 'zenml_pipeline_name': 'mlflow_training_pipeline',                       ┃
┃                        │               │                                         │ 'zenml_pipeline_run_uuid': '11858dcf-3e47-4b1a-82c5-6fa25ba4e037', 'epochs': '5', 'optimizer': 'Adam', 'lr': '0.003'}     ┃
┠────────────────────────┼───────────────┼─────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┨
┃ tensorflow-mnist-model │ 1             │ Run #1 of the mlflow_training_pipeline. │ {'zenml_version': '0.34.0', 'zenml_run_name': 'mlflow_training_pipeline-2023_03_01-08_08_52_398499', 'zenml_pipeline_name': 'mlflow_training_pipeline',                       ┃
┃                        │               │                                         │ 'zenml_pipeline_run_uuid': '29fb22c1-6e0b-4431-9e04-226226506d16', 'epochs': '5', 'optimizer': 'Adam', 'lr': '0.001'}     ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

For more details on a specific model version, you can use the `zenml model-registry models get-version REGISTERED_MODEL_NAME -v VERSION` command:

```shell
$ zenml model-registry models get-version tensorflow-mnist-model -v 1

┏━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ MODEL VERSION PROPERTY │ VALUE                                                                                                                                                                                                                                          ┃
┠────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┨
┃ REGISTERED_MODEL_NAME  │ tensorflow-mnist-model                                                                                                                                                                                                                         ┃
┠────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┨
┃ VERSION                │ 1                                                                                                                                                                                                                                              ┃
┠────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┨
┃ VERSION_DESCRIPTION    │ Run #1 of the mlflow_training_pipeline.                                                                                                                                                                                                        ┃
┠────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┨
┃ CREATED_AT             │ 2023-03-01 09:09:06.899000                                                                                                                                                                                                                     ┃
┠────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┨
┃ UPDATED_AT             │ 2023-03-01 09:09:06.899000                                                                                                                                                                                                                     ┃
┠────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┨
┃ METADATA               │ {'zenml_version': '0.34.0', 'zenml_run_name': 'mlflow_training_pipeline-2023_03_01-08_08_52_398499', 'zenml_pipeline_name': 'mlflow_training_pipeline', 'zenml_pipeline_run_uuid': '29fb22c1-6e0b-4431-9e04-226226506d16',              ┃
┃                        │ 'lr': '0.001', 'epochs': '5', 'optimizer': 'Adam'}                                                                                                                                  ┃
┠────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┨
┃ MODEL_SOURCE_URI       │ file:///Users/safoine-zenml/Library/Application Support/zenml/local_stores/0902a511-117d-4152-a098-b2f1124c4493/mlruns/489728212459131640/293a0d2e71e046999f77a79639f6eac2/artifacts/model                                                     ┃
┠────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┨
┃ STAGE                  │ None                                                                                                                                                                                                                                           ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

Finally, to delete a registered model or a specific model version, you can use the `zenml model-registry models delete REGISTERED_MODEL_NAME` and `zenml model-registry models delete-version REGISTERED_MODEL_NAME -v VERSION` commands respectively.

Check out the [SDK docs](https://sdkdocs.zenml.io/latest/integration\_code\_docs/integrations-mlflow/#zenml.integrations.mlflow.model\_registry.MLFlowModelRegistry) to see more about the interface and implementation.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
