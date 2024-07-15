---
description: >-
  Deploying models to Databricks Inference Endpoints with Databricks
---

# Databricks


Databricks Model Serving or Mosaic AI Model Serving provides a unified interface to deploy, govern, and query AI models. Each model you serve is available as a REST API that you can integrate into your web or client application.

This service provides dedicated and autoscaling infrastructure managed by Databricks, allowing you to deploy models without dealing with containers and GPUs.


{% hint style="info" %}
Databricks Model deployer can be considered as a managed service for deploying models using MLflow, This means you can switch between MLflow and Databricks Model Deployers without changing your pipeline code even for custom complex models.
{% endhint %}

## When to use it?

You should use Databricks Model Deployer:

*   You are already using Databricks for your data and ML workloads.
*   If you want to deploy AI models without dealing with containers and GPUs, Databricks Model Deployer provides a unified interface to deploy, govern, and query models.
*   Databricks Model Deployer offers dedicated and autoscaling infrastructure managed by Databricks, making it easier to deploy models at scale.
*   Enterprise security is a priority, and you need to deploy models into secure offline endpoints accessible only via a direct connection to your Virtual Private Cloud (VPCs).
*   if your goal is to turn your models into production-ready APIs with minimal infrastructure or MLOps involvement.


If you are looking for a more easy way to deploy your models locally, you can use the [MLflow Model Deployer](mlflow.md) flavor.

## How to deploy it?

The Databricks Model Deployer flavor is provided by the Databricks ZenML integration, so you need to install it on your local machine to be able to deploy your models. You can do this by running the following command:

```bash
zenml integration install databricks -y
```

To register the Databricks model deployer with ZenML you need to run the following command:

```bash
zenml model-deployer register <MODEL_DEPLOYER_NAME> --flavor=databricks --host=<HOST> --client_id={{databricks.client_id}} --client_secret={{databricks.client_secret}}
```

{% hint style="info" %}
We recommend creating a Databricks service account with the necessary permissions to create and run jobs. You can find more information on how to create a service account [here](https://docs.databricks.com/dev-tools/api/latest/authentication.html). You can generate a client_id and client_secret for the service account and use them to authenticate with Databricks.
{% endhint %}

We can now use the model deployer in our stack.

```bash
zenml stack update <CUSTOM_STACK_NAME> --model-deployer=<MODEL_DEPLOYER_NAME>
```

See the [databricks\_model\_deployer\_step](https://sdkdocs.zenml.io/latest/integration\_code\_docs/integrations-databricks/#zenml.integrations.databricks.steps.databricks\_deployer.databricks\_model\_deployer\_step) for an example of using the Databricks Model Deployer to deploy a model inside a ZenML pipeline step.

## Configuration

Within the `DatabricksServiceConfig` you can configure:


* `model_name`: The name of the model that will be served, this will be used to identify the model in the Databricks Model Registry.
* `model_version`: The version of the model that will be served, this will be used to identify the model in the Databricks Model Registry.
* `workload_size`: The size of the workload that the model will be serving. This can be `ServedModelInputWorkloadSize.SMALL`, `ServedModelInputWorkloadSize.MEDIUM`, or `ServedModelInputWorkloadSize.LARGE`, you can import this enum from `from databricks.sdk.service.serving import ServedModelInputWorkloadSize`.
* `scale_to_zero_enabled`: A boolean flag to enable or disable the scale to zero feature.
* `env_vars`: A dictionary of environment variables to be passed to the model serving container.
* `workload_type`: The type of workload that the model will be serving. This can be `ServedModelInputWorkloadType.CPU`, `ServedModelInputWorkloadType.GPU_LARGE`, `ServedModelInputWorkloadType.GPU_MEDIUM`, `ServedModelInputWorkloadType.GPU_SMALL`, or `ServedModelInputWorkloadType.MULTIGPU_MEDIUM`, you can import this enum from `from databricks.sdk.service.serving import ServedModelInputWorkloadType`.
* `endpoint_secret_name`: The name of the secret that will be used to secure the endpoint and authenticate requests.

For more information and a full list of configurable attributes of the Databricks Model Deployer, check out the [SDK Docs](https://sdkdocs.zenml.io/latest/integration\_code\_docs/integrations-databricks/#zenml.integrations.databricks.model\_deployers) and Databricks endpoint [code](https://github.com/databricks/databricks\_hub/blob/5e3b603ccc7cd6523d998e75f82848215abf9415/src/databricks\_hub/hf\_api.py#L6957).

### Run inference on a provisioned inference endpoint

The following code example shows how to run inference against a provisioned inference endpoint:

```python
from typing import Annotated
from zenml import step, pipeline
from zenml.integrations.databricks.model_deployers import DatabricksModelDeployer
from zenml.integrations.databricks.services import DatabricksDeploymentService


# Load a prediction service deployed in another pipeline
@step(enable_cache=False)
def prediction_service_loader(
    pipeline_name: str,
    pipeline_step_name: str,
    running: bool = True,
    model_name: str = "default",
) -> DatabricksDeploymentService:
    """Get the prediction service started by the deployment pipeline.

    Args:
        pipeline_name: name of the pipeline that deployed the MLflow prediction
            server
        step_name: the name of the step that deployed the MLflow prediction
            server
        running: when this flag is set, the step only returns a running service
        model_name: the name of the model that is deployed
    """
    # get the Databricks model deployer stack component
    model_deployer = DatabricksModelDeployer.get_active_model_deployer()

    # fetch existing services with same pipeline name, step name and model name
    existing_services = model_deployer.find_model_server(
        pipeline_name=pipeline_name,
        pipeline_step_name=pipeline_step_name,
        model_name=model_name,
        running=running,
    )

    if not existing_services:
        raise RuntimeError(
            f"No Databricks inference endpoint deployed by step "
            f"'{pipeline_step_name}' in pipeline '{pipeline_name}' with name "
            f"'{model_name}' is currently running."
        )

    return existing_services[0]


# Use the service for inference
@step
def predictor(
    service: DatabricksDeploymentService,
    data: str
) -> Annotated[str, "predictions"]:
    """Run a inference request against a prediction service"""

    prediction = service.predict(data)
    return prediction


@pipeline
def databricks_deployment_inference_pipeline(
    pipeline_name: str, pipeline_step_name: str = "databricks_model_deployer_step",
):
    inference_data = ...
    model_deployment_service = prediction_service_loader(
        pipeline_name=pipeline_name,
        pipeline_step_name=pipeline_step_name,
    )
    predictions = predictor(model_deployment_service, inference_data)
```

For more information and a full list of configurable attributes of the Databricks Model Deployer, check out the [SDK Docs](https://sdkdocs.zenml.io/latest/integration\_code\_docs/integrations-databricks/#zenml.integrations.databricks.model\_deployers).

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
