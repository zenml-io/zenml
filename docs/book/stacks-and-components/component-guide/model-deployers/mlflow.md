---
description: Deploying your models locally with MLflow.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To check the latest version please [visit https://docs.zenml.io](https://docs.zenml.io)
{% endhint %}


# MLflow

The MLflow Model Deployer is one of the available flavors of the [Model Deployer](model-deployers.md) stack component.
Provided with the MLflow integration it can be used to deploy and
manage [MLflow models](https://www.mlflow.org/docs/latest/python\_api/mlflow.deployments.html) on a local running MLflow
server.

{% hint style="warning" %}
The MLflow Model Deployer is not yet available for use in production. This is a work in progress and will be available
soon. At the moment it is only available for use in a local development environment.
{% endhint %}

## When to use it?

MLflow is a popular open-source platform for machine learning. It's a great tool for managing the entire lifecycle of
your machine learning. One of the most important features of MLflow is the ability to package your model and its
dependencies into a single artifact that can be deployed to a variety of deployment targets.

You should use the MLflow Model Deployer:

* if you want to have an easy way to deploy your models locally and perform real-time predictions using the running
  MLflow prediction server.
* if you are looking to deploy your models in a simple way without the need for a dedicated deployment environment like
  Kubernetes or advanced infrastructure configuration.

If you are looking to deploy your models in a more complex way, you should use one of the
other [Model Deployer Flavors](model-deployers.md#model-deployers-flavors) available in ZenML.

## How do you deploy it?

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

## How do you use it?

### Deploy a logged model

ZenML provides a predefined `mlflow_model_deployer_step` that you can use to 
deploy an MLflfow prediction service based on a model that you have 
previously logged in your 
[MLflow experiment tracker](../experiment-trackers/mlflow.md):

```python
from zenml import pipeline
from zenml.integrations.mlflow.steps import mlflow_model_deployer_step

@pipeline
def mlflow_train_deploy_pipeline():
    model = ...
    deployed_model = mlflow_model_deployer_step(model=model)
```

{% hint style="warning" %}
The `mlflow_model_deployer_step` expects that the `model` it receives has 
already been logged to MLflow in a previous step. E.g., for a scikit-learn 
model, you would need to have used `mlflow.sklearn.autolog()` or 
`mlflow.sklearn.log_model(model)` in a previous step. See the
[MLflow experiment tracker documentation](../experiment-trackers/mlflow.md) for
more information on how to log models to MLflow from your ZenML steps.
{% endhint %}

### Deploy from model registry

Alternatively, if you are already using the 
[MLflow model registry](../model-registries/mlflow.md), you can use the
`mlflow_model_registry_deployer_step` to directly deploy an MLflow prediction
service based on a model in your model registry:

```python
from zenml import pipeline
from zenml.integrations.mlflow.steps import mlflow_model_registry_deployer_step

@pipeline
def mlflow_registry_deploy_pipeline():
    deployed_model = mlflow_model_registry_deployer_step(
        registry_model_name="tensorflow-mnist-model",
        registry_model_version="1",  # Either specify a model version
        # or use the model stage if you have set it in the MLflow registry:
        # registered_model_stage="Staging"
    )
```

See the [MLflow model registry documentation](../model-registries/mlflow.md)
for more information on how to register models in the MLflow registry.

### Run inference on a deployed model

The following code example shows how you can load a deployed model in Python
and run inference against it:


```python
from zenml import step
from zenml.integrations.mlflow.model_deployers.mlflow_model_deployer import (
    MLFlowModelDeployer,
)
from zenml.integrations.mlflow.services import MLFlowDeploymentService


# Load a prediction service deployed in another pipeline
@step(enable_cache=False)
def prediction_service_loader(
    pipeline_name: str,
    pipeline_step_name: str,
    running: bool = True,
    model_name: str = "model",
) -> MLFlowDeploymentService:
    """Get the prediction service started by the deployment pipeline.

    Args:
        pipeline_name: name of the pipeline that deployed the MLflow prediction
            server
        step_name: the name of the step that deployed the MLflow prediction
            server
        running: when this flag is set, the step only returns a running service
        model_name: the name of the model that is deployed
    """
    # get the MLflow model deployer stack component
    model_deployer = MLFlowModelDeployer.get_active_model_deployer()

    # fetch existing services with same pipeline name, step name and model name
    existing_services = model_deployer.find_model_server(
        pipeline_name=pipeline_name,
        pipeline_step_name=pipeline_step_name,
        model_name=model_name,
        running=running,
    )

    if not existing_services:
        raise RuntimeError(
            f"No MLflow prediction service deployed by step "
            f"'{pipeline_step_name}' in pipeline '{pipeline_name}' with name "
            f"'{model_name}' is currently running."
        )

    return existing_services[0]


# Use the service for inference
@step
def predictor(
    service: MLFlowDeploymentService,
    data: np.ndarray,
) -> Annotated[np.ndarray, "predictions"]:
    """Run a inference request against a prediction service"""

    service.start(timeout=10)  # should be a NOP if already started
    prediction = service.predict(data)
    prediction = prediction.argmax(axis=-1)

    return prediction


@pipeline
def mlflow_deployment_inference_pipeline(
    pipeline_name: str, pipeline_step_name: str = "mlflow_model_deployer_step",
):
    inference_data = ...
    model_deployment_service = prediction_service_loader(
        pipeline_name=pipeline_name,
        pipeline_step_name=pipeline_step_name,
    )
    predictions = predictor(model_deployment_service, inference_data)
```

For more information and a full list of configurable attributes of the MLflow Model Deployer, check out
the [SDK Docs](https://sdkdocs.zenml.io/latest/integration\_code\_docs/integrations-mlflow/#zenml.integrations.mlflow.model\_deployers)
.

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
