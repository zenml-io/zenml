---
description: Managing MLFlow logged models and artifacts
---

# MLflow Model Registry

The MLflow Model Registry is a [model registry](model-registries.md) flavor provided with the MLflow ZenML integration
that uses [the MLflow model registry service](https://mlflow.org/docs/latest/model-registry.html) to manage and track ML
models and their artifacts.

### When would you want to use it?

[MLflow Model Registry](https://mlflow.org/docs/latest/model-registry.html)) is a powerful tool that you would typically
use in the experimenting, QA, and production phase to manage and track machine learning model versions. It is designed
to help teams collaborate on model development and deployment, and keep track of which models are being used in which
environments. With MLflow Model Registry, you can store and manage models, deploy them to different environments, and
track their performance over time. This tool is useful in the following scenarios:

* If you are working on a machine learning project and want to keep track of different model versions as they are
  developed and deployed.
* If you need to deploy machine learning models to different environments and want to keep track of which version is
  being used in each environment.
* If you want to monitor and compare the performance of different model versions over time and make data-driven
  decisions about which models to use in production.
* If you want to simplify the process of deploying models either to a production environment or to a staging environment
  for testing.

### How do you deploy it?

The MLflow Model Registry flavor is provided by the MLflow ZenML integration, 
so you need to install it on your local machine to be able to register an 
MLflow Model Registry component:

```shell
zenml integration install mlflow -y
```

Once the MLflow integration is installed, you can register an MLflow Model Registry component in your stack:

```shell
zenml model-registry register mlflow_model_registry --flavor=mlflow

# Register and set a stack with the new model registry as the active stack
zenml stack register custom_stack -r mlflow_model_registry ... --set
```

#### Authentication Methods

To register models from a remote MLflow tracking server, you need to configure 
the following authentication credentials:

* `tracking_uri`: The URL pointing to the MLflow tracking server. If using an MLflow Tracking Server managed by
  Databricks, then the value of this attribute should be `"databricks"`.
* `tracking_username`: Username for authenticating with the MLflow tracking server.
* `tracking_password`: Password for authenticating with the MLflow tracking server.
* `tracking_token` (in place of `tracking_username` and `tracking_password`): Token for authenticating with the MLflow
  tracking server.
* `tracking_insecure_tls` (optional): Set to skip verifying the MLflow tracking server SSL certificate.
* `databricks_host`: The host of the Databricks workspace with the MLflow-managed server to connect to. This is only
  required if the `tracking_uri` value is set to `"databricks"`. More
  information: [Access the MLflow tracking server from outside Databricks](https://docs.databricks.com/applications/mlflow/access-hosted-tracking-server.html)

See the [MLflow Experiment Tracker Documentation](../experiment-trackers/mlflow.md#authentication-methods)
for more information on these credentials.

### How do you use it?

There are different ways to use the MLflow Model Registry. You can use it in your ZenML pipelines with the built-in
step, or you can use the ZenML CLI to register your model manually or call the Model Registry API within a custom step
in your pipeline. The following sections show you how to use the MLflow Model Registry in your ZenML pipelines and with
the ZenML CLI:

#### Built-in MLflow Model Registry step

After registering the MLflow Model Registry component in your stack, you can use it in a pipeline by using
the `mlflow_model_registry_step` which is a built-in step that is provided by the MLflow ZenML integration. This step
automatically registers the model that was produced by the previous step in the pipeline:

```python
@step
def training_data_loader():
    ...
  
@step
def svc_trainer():
    ...

from zenml.integrations.mlflow.steps.mlflow_registry import mlflow_register_model_step

@pipeline
def training_pipeline():
    """Train, evaluate, and deploy a model."""
    X_train, X_test, y_train, y_test = training_data_loader()
    model = svc_trainer(X_train=X_train, y_train=y_train)
    mlflow_register_model_step(
        model,
        name="zenml-quickstart-model",
        metadata=ModelRegistryModelMetadata(gamma=0.01, arch="svc"),
        description="The first run of the Quickstart pipeline.",
    )
```

#### Model Registry CLI Commands

Sometimes adding a step to your pipeline is not the best option for you, as it will register the model in the MLflow
Model Registry every time you run the pipeline. In this case, you can use the ZenML CLI to register your model manually.
The CLI provides a command called `zenml model-registry models register-version` that you can use to register your model
in the MLflow Model Registry.

```shell
zenml model-registry models register-version Tensorflow-model \
    --description="A new version of the tensorflow model with accuracy 98.88%" \
    -v 1 \
    --model-uri="file:///.../mlruns/667102566783201219/3973eabc151c41e6ab98baeb20c5323b/artifacts/model" \
    -m key1 value1 -m key2 value2 \
    --zenml-pipeline-name="mlflow_training_pipeline" \
    --zenml-step-name="trainer"
```

#### List of available parameters

To register a model version in the MLflow Model Registry, you need to provide a list of parameters. when you use the
built-in step, most of the parameters are automatically filled in for you. However, you can still override them if you
want to. The following table shows the list of available parameters.

* `name`: The name of the model. This is a required parameter.
* `model_source_uri`: The path to the model. This is a required parameter.
* `description`: A description of the model version.
* `metadata`: A list of metadata to associate with the model version of the type `ModelRegistryModelMetadata`.

{% hint style="info" %}
The `model_uri` parameter is the path to the model within the MLflow tracking server. If you are using a local MLflow
tracking server, the path will be something
like `file:///.../mlruns/667102566783201219/3973eabc151c41e6ab98baeb20c5323b/artifacts/model`. If you are using a remote
MLflow tracking server, the path will be something
like `s3://.../mlruns/667102566783201219/3973eabc151c41e6ab98baeb20c5323b/artifacts/model`.

You can find the path of the model in the MLflow UI. Go to the `Artifacts` tab of the run that produced the model and
click on the model. The path will be displayed in the URL.

<img src="../../../assets/mlflow/mlflow_ui_uri.png" alt="MLflow UI" data-size="original">
{% endhint %}

Check out
the [API docs](https://apidocs.zenml.io/latest/integration\_code\_docs/integrations-mlflow/#zenml.integrations.mlflow.model\_registry.MLFlowModelRegistry)
to see more about the interface and implementation. You can
also [check out our examples page](https://github.com/zenml-io/zenml/tree/main/examples/mlflow\_registry) for a working
example that uses the MLflow Model Registry.
