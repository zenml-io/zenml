---
description: Deploying your models locally with MLflow.
---

# MLflow

The MLflow Model Deployer is one of the available flavors of the [Model Deployer](model-deployers.md) stack component.
Provided with the MLflow integration it can be used to deploy and
manage [MLflow models](https://www.mlflow.org/docs/latest/python\_api/mlflow.deployments.html) on a local running MLflow
server.

{% hint style="warning" %}
The MLflow Model Deployer is not yet available for use in production. This is a work in progress and will be available
soon. At the moment it is only available for use in a local development environment.
{% endhint %}

### When to use it?

MLflow is a popular open-source platform for machine learning. It's a great tool for managing the entire lifecycle of
your machine learning. One of the most important features of MLflow is the ability to package your model and its
dependencies into a single artifact that can be deployed to a variety of deployment targets.

You should use the MLflow Model Deployer:

* if you want to have an easy way to deploy your models locally and perform real-time predictions using the running
  MLflow prediction server.
* if you are looking to deploy your models in a simple way without the need for a dedicated deployment environment like
  Kubernetes or advanced infrastructure configuration.

If you are looking to deploy your models in a more complex way, you should use one of the
other [Model Deployer Flavors](model-deployers.md#model-deployers-flavors) available in ZenML (e.g. Seldon Core, KServe,
etc.)

### How do you deploy it?

The MLflow Model Deployer flavor is provided by the MLflow ZenML integration, so you need to install it on your local
machine to be able to deploy your models. You can do this by running the following command:

```bash
zenml integration install mlflow -y
```

To register the MLflow model deployer with ZenML you need to run the following command:

```bash
zenml model-deployer register mlflow_deployer --flavor=mlflow
```

The ZenML integration will provision a local MLflow deployment server as a daemon process that will continue to run in
the background to serve the latest MLflow model.

#### Authentication Methods

To deploy models from a remote MLflow tracking server, you need to configure 
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

After registering the MLflow Model Deloyer component in your stack, you can use it in a pipeline by using
the `mlflow_model_deployer_step` which is a built-in step that is provided by the MLflow ZenML integration. This step
automatically deploys the model that was produced by the previous step in the pipeline:

```python
@step
def training_data_loader():
    ...
  
@step
def svc_trainer():
    ...

from zenml.integrations.mlflow.steps.mlflow_deployer import mlflow_model_deployer_step


@pipeline
def training_pipeline():
    """Train, evaluate, and deploy a model."""
    X_train, X_test, y_train, y_test = training_data_loader()
    model = svc_trainer(X_train=X_train, y_train=y_train)
    mlflow_model_deployer_step(model)
```