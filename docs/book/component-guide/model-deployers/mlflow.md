---
description: Deploying your models locally with MLflow.
---

# MLflow

The MLflow Model Deployer is one of the available flavors of the [Model Deployer](./model-deployers.md) stack component. Provided with the MLflow integration it can be used to deploy and manage [MLflow models](https://www.mlflow.org/docs/latest/python\_api/mlflow.deployments.html) on a local running MLflow server.

{% hint style="warning" %}
The MLflow Model Deployer is not yet available for use in production. This is a work in progress and will be available soon. At the moment it is only available for use in a local development environment.
{% endhint %}

## When to use it?

MLflow is a popular open-source platform for machine learning. It's a great tool for managing the entire lifecycle of your machine learning. One of the most important features of MLflow is the ability to package your model and its dependencies into a single artifact that can be deployed to a variety of deployment targets.

You should use the MLflow Model Deployer:

* if you want to have an easy way to deploy your models locally and perform real-time predictions using the running MLflow prediction server.
* if you are looking to deploy your models in a simple way without the need for a dedicated deployment environment like Kubernetes or advanced infrastructure configuration.

If you are looking to deploy your models in a more complex way, you should use one of the other [Model Deployer Flavors](./model-deployers.md#model-deployers-flavors) available in ZenML.

## How do you deploy it?

The MLflow Model Deployer flavor is provided by the MLflow ZenML integration, so you need to install it on your local machine to be able to deploy your models. You can do this by running the following command:

```bash
zenml integration install mlflow -y
```

To register the MLflow model deployer with ZenML you need to run the following command:

```bash
zenml model-deployer register mlflow_deployer --flavor=mlflow
```

The ZenML integration will provision a local MLflow deployment server as a daemon process that will continue to run in the background to serve the latest MLflow model.

## How do you use it?

### Deploy a logged model

Following [MLflow's documentation](https://mlflow.org/docs/latest/deployment/deploy-model-locally.html#deploy-mlflow-model-as-a-local-inference-server), if we want to deploy a model as a local inference server, we need the model to be logged in the MLflow experiment tracker first. Once the model is logged, we can use the model URI either from the artifact path saved with the MLflow run or using model name and version if a model is registered in the MLflow model registry.

In the following examples, we will show how to deploy a model using the MLflow Model Deployer, in two different scenarios:

1. We already know the logged model URI and we want to deploy it as a local inference server.

```python
from zenml import pipeline, step, get_step_context
from zenml.client import Client

@step
def deploy_model() -> Optional[MLFlowDeploymentService]:
    # Deploy a model using the MLflow Model Deployer
    zenml_client = Client()
    model_deployer = zenml_client.active_stack.model_deployer
    mlflow_deployment_config = MLFlowDeploymentConfig(
        name: str = "mlflow-model-deployment-example",
        description: str = "An example of deploying a model using the MLflow Model Deployer",
        pipeline_name: str = get_step_context().pipeline_name,
        pipeline_step_name: str = get_step_context().step_name,
        model_uri: str = "runs:/<run_id>/model" or "models:/<model_name>/<model_version>",
        model_name: str = "model",
        workers: int = 1
        mlserver: bool = False
        timeout: int = DEFAULT_SERVICE_START_STOP_TIMEOUT
    )
    service = model_deployer.deploy_model(
        config=mlflow_deployment_config, 
        service_type=MLFlowDeploymentService.SERVICE_TYPE
    )
    logger.info(f"The deployed service info: {model_deployer.get_model_server_info(service)}")
    return service
```

2. We don't know the logged model URI, since the model was logged in a previous step. We want to deploy the model as a local inference server. ZenML provides set of functionalities that would make it easier to get the model URI from the current run and deploy it.

```python
from zenml import pipeline, step, get_step_context
from zenml.client import Client
from mlflow.tracking import MlflowClient, artifact_utils


@step
def deploy_model() -> Optional[MLFlowDeploymentService]:
    # Deploy a model using the MLflow Model Deployer
    zenml_client = Client()
    model_deployer = zenml_client.active_stack.model_deployer
    experiment_tracker = zenml_client.active_stack.experiment_tracker
    # Let's get the run id of the current pipeline
    mlflow_run_id = experiment_tracker.get_run_id(
        experiment_name=get_step_context().pipeline_name,
        run_name=get_step_context().run_name,
    )
    # Once we have the run id, we can get the model URI using mlflow client
    experiment_tracker.configure_mlflow()
    client = MlflowClient()
    model_name = "model" # set the model name that was logged
    model_uri = artifact_utils.get_artifact_uri(
        run_id=mlflow_run_id, artifact_path=model_name
    )
    mlflow_deployment_config = MLFlowDeploymentConfig(
        name: str = "mlflow-model-deployment-example",
        description: str = "An example of deploying a model using the MLflow Model Deployer",
        pipeline_name: str = get_step_context().pipeline_name,
        pipeline_step_name: str = get_step_context().step_name,
        model_uri: str = model_uri,
        model_name: str = model_name,
        workers: int = 1,
        mlserver: bool = False,
        timeout: int = 300,
    )
    service = model_deployer.deploy_model(
        config=mlflow_deployment_config, 
        service_type=MLFlowDeploymentService.SERVICE_TYPE
    )
    return service
```

#### Configuration

Within the `MLFlowDeploymentService` you can configure:

* `name`: The name of the deployment.
* `description`: The description of the deployment.
* `pipeline_name`: The name of the pipeline that deployed the MLflow prediction server.
* `pipeline_step_name`: The name of the step that deployed the MLflow prediction server.
* `model_name`: The name of the model that is deployed in case of model registry the name must be a valid registered model name.
* `model_version`: The version of the model that is deployed in case of model registry the version must be a valid registered model version.
* `silent_daemon`: set to True to suppress the output of the daemon (i.e., redirect stdout and stderr to /dev/null). If False, the daemon output will be redirected to a log file.
* `blocking`: set to True to run the service in the context of the current process and block until the service is stopped instead of running the service as a daemon process. Useful for operating systems that do not support daemon processes.
* `model_uri`: The URI of the model to be deployed. This can be a local file path, a run ID, or a model name and version.
* `workers`: The number of workers to be used by the MLflow prediction server.
* `mlserver`: If True, the MLflow prediction server will be started as a MLServer instance.
* `timeout`: The timeout in seconds to wait for the MLflow prediction server to start or stop.

### Run inference on a deployed model

The following code example shows how you can load a deployed model in Python and run inference against it:

1. Load a prediction service deployed in another pipeline

```python
import json
import requests
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
    model_name: str = "model",
) -> None:
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
    )

    if not existing_services:
        raise RuntimeError(
            f"No MLflow prediction service deployed by step "
            f"'{pipeline_step_name}' in pipeline '{pipeline_name}' with name "
            f"'{model_name}' is currently running."
        )

    service = existing_services[0]

    # Let's try run a inference request against the prediction service

    payload = json.dumps(
        {
            "inputs": {"messages": [{"role": "user", "content": "Tell a joke!"}]},
            "params": {
                "temperature": 0.5,
                "max_tokens": 20,
            },
        }
    )
    response = requests.post(
        url=service.get_prediction_url(),
        data=payload,
        headers={"Content-Type": "application/json"},
    )

    response.json()
```

2. Within the same pipeline, use the service from previous step to run inference this time using pre-built predict method

```python
from typing_extensions import Annotated
import numpy as np
from zenml import step
from zenml.integrations.mlflow.services import MLFlowDeploymentService

# Use the service for inference
@step
def predictor(
    service: MLFlowDeploymentService,
    data: np.ndarray,
) -> Annotated[np.ndarray, "predictions"]:
    """Run a inference request against a prediction service"""

    prediction = service.predict(data)
    prediction = prediction.argmax(axis=-1)

    return prediction
```

For more information and a full list of configurable attributes of the MLflow Model Deployer, check out the [SDK Docs](https://sdkdocs.zenml.io/latest/integration\_code\_docs/integrations-mlflow/#zenml.integrations.mlflow.model\_deployers) .

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
