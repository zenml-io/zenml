---
description: >-
  Deploying models to Huggingface Inference Endpoints with Hugging Face
  :hugging_face:.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Hugging Face

Hugging Face Inference Endpoints provides a secure production solution to easily deploy any `transformers`, `sentence-transformers`, and `diffusers` models on a dedicated and autoscaling infrastructure managed by Hugging Face. An Inference Endpoint is built from a model from the [Hub](https://huggingface.co/models).

This service provides dedicated and autoscaling infrastructure managed by Hugging Face, allowing you to deploy models without dealing with containers and GPUs.

## When to use it?

You should use Hugging Face Model Deployer:

* if you want to deploy [Transformers, Sentence-Transformers, or Diffusion models](https://huggingface.co/docs/inference-endpoints/supported\_tasks) on dedicated and secure infrastructure.
* if you prefer a fully-managed production solution for inference without the need to handle containers and GPUs.
* if your goal is to turn your models into production-ready APIs with minimal infrastructure or MLOps involvement
* Cost-effectiveness is crucial, and you want to pay only for the raw compute resources you use.
* Enterprise security is a priority, and you need to deploy models into secure offline endpoints accessible only via a direct connection to your Virtual Private Cloud (VPCs).

If you are looking for a more easy way to deploy your models locally, you can use the [MLflow Model Deployer](mlflow.md) flavor.

## How to deploy it?

The Hugging Face Model Deployer flavor is provided by the Hugging Face ZenML integration, so you need to install it on your local machine to be able to deploy your models. You can do this by running the following command:

```bash
zenml integration install huggingface -y
```

To register the Hugging Face model deployer with ZenML you need to run the following command:

```bash
zenml model-deployer register <MODEL_DEPLOYER_NAME> --flavor=huggingface --token=<YOUR_HF_TOKEN> --namespace=<YOUR_HF_NAMESPACE>
```

Here,

* `token` parameter is the Hugging Face authentication token. It can be managed through [Hugging Face settings](https://huggingface.co/settings/tokens).
* `namespace` parameter is used for listing and creating the inference endpoints. It can take any of the following values, username or organization name or `*` depending on where the inference endpoint should be created.

We can now use the model deployer in our stack.

```bash
zenml stack update <CUSTOM_STACK_NAME> --model-deployer=<MODEL_DEPLOYER_NAME>
```

## How to use it

There are two mechanisms for using the Hugging Face model deployer integration:

* Using the pre-built [huggingface\_model\_deployer\_step](https://github.com/zenml-io/zenml/blob/main/src/zenml/integrations/huggingface/steps/huggingface_deployer.py#L35) to deploy a Hugging Face model.
* Running batch inference on a deployed Hugging Face model using the [HuggingFaceDeploymentService](https://github.com/zenml-io/zenml/blob/04cdf96576edd8fc615dceb7e0bf549301dc97bd/tests/integration/examples/huggingface/steps/prediction_service_loader/prediction_service_loader.py#L27)

If you'd like to see this in action, check out this example of of [a deployment pipeline](https://github.com/zenml-io/zenml/blob/main/tests/integration/examples/huggingface/pipelines/deployment_pipelines/deployment_pipeline.py#L29) and [an inference pipeline](https://github.com/zenml-io/zenml/blob/main/tests/integration/examples/huggingface/pipelines/deployment_pipelines/inference_pipeline.py).

### Deploying a model

The pre-built [huggingface\_model\_deployer\_step](https://github.com/zenml-io/zenml/blob/main/src/zenml/integrations/huggingface/steps/huggingface_deployer.py#L35) exposes a [`HuggingFaceServiceConfig`](https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-huggingface/#zenml.integrations.huggingface.services.huggingface_deployment.HuggingFaceServiceConfig) that you can use in your pipeline. Here is an example snippet:

```python
from zenml import pipeline
from zenml.config import DockerSettings
from zenml.integrations.constants import HUGGINGFACE
from zenml.integrations.huggingface.services import HuggingFaceServiceConfig
from zenml.integrations.huggingface.steps import (
    huggingface_model_deployer_step,
)

docker_settings = DockerSettings(
    required_integrations=[HUGGINGFACE],
)


@pipeline(enable_cache=True, settings={"docker": docker_settings})
def huggingface_deployment_pipeline(
    model_name: str = "hf",
    timeout: int = 1200,
):
    service_config = HuggingFaceServiceConfig(model_name=model_name)

    # Deployment step
    huggingface_model_deployer_step(
        service_config=service_config,
        timeout=timeout,
    )
```

Within the `HuggingFaceServiceConfig` you can configure:

* `model_name`: the name of the model in ZenML.
* `endpoint_name`: the name of the inference endpoint. We add a prefix `zenml-` and first 8 characters of the service uuid as a suffix to the endpoint name.
* `repository`: The repository name in the user’s namespace (`{username}/{model_id}`) or in the organization namespace (`{organization}/{model_id}`) from the Hugging Face hub.
* `framework`: The machine learning framework used for the model (e.g. `"custom"`, `"pytorch"` )
* `accelerator`: The hardware accelerator to be used for inference. (e.g. `"cpu"`, `"gpu"`)
* `instance_size`: The size of the instance to be used for hosting the model (e.g. `"large"`, `"xxlarge"`)
* `instance_type`: Inference Endpoints offers a selection of curated CPU and GPU instances. (e.g. `"c6i"`, `"g5.12xlarge"`)
* `region`: The cloud region in which the Inference Endpoint will be created (e.g. `"us-east-1"`, `"eu-west-1"` for `vendor = aws` and `"eastus"` for Microsoft Azure vendor.).
* `vendor`: The cloud provider or vendor where the Inference Endpoint will be hosted (e.g. `"aws"`).
* `token`: The Hugging Face authentication token. It can be managed through [huggingface settings](https://huggingface.co/settings/tokens). The same token can be passed used while registering the Hugging Face model deployer.
* `account_id`: (Optional) The account ID used to link a VPC to a private Inference Endpoint (if applicable).
* `min_replica`: (Optional) The minimum number of replicas (instances) to keep running for the Inference Endpoint. Defaults to `0`.
* `max_replica`: (Optional) The maximum number of replicas (instances) to scale to for the Inference Endpoint. Defaults to `1`.
* `revision`: (Optional) The specific model revision to deploy on the Inference Endpoint for the Hugging Face repository .
* `task`: Select a supported [Machine Learning Task](https://huggingface.co/docs/inference-endpoints/supported\_tasks). (e.g. `"text-classification"`, `"text-generation"`)
* `custom_image`: (Optional) A custom Docker image to use for the Inference Endpoint.
* `namespace`: The namespace where the Inference Endpoint will be created. The same namespace can be passed used while registering the Hugging Face model deployer.
* `endpoint_type`: (Optional) The type of the Inference Endpoint, which can be `"protected"`, `"public"` (default) or `"private"`.

For more information and a full list of configurable attributes of the Hugging Face Model Deployer, check out the [SDK Docs](https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-huggingface/) and Hugging Face endpoint [code](https://github.com/huggingface/huggingface_hub/blob/5e3b603ccc7cd6523d998e75f82848215abf9415/src/huggingface_hub/hf_api.py#L6957).

### Running inference on a provisioned inference endpoint

The following code example shows how to run inference against a provisioned inference endpoint:

```python
from typing import Annotated
from zenml import step, pipeline
from zenml.integrations.huggingface.model_deployers import HuggingFaceModelDeployer
from zenml.integrations.huggingface.services import HuggingFaceDeploymentService


# Load a prediction service deployed in another pipeline
@step(enable_cache=False)
def prediction_service_loader(
    pipeline_name: str,
    pipeline_step_name: str,
    running: bool = True,
    model_name: str = "default",
) -> HuggingFaceDeploymentService:
    """Get the prediction service started by the deployment pipeline.

    Args:
        pipeline_name: name of the pipeline that deployed the MLflow prediction
            server
        step_name: the name of the step that deployed the MLflow prediction
            server
        running: when this flag is set, the step only returns a running service
        model_name: the name of the model that is deployed
    """
    # get the Hugging Face model deployer stack component
    model_deployer = HuggingFaceModelDeployer.get_active_model_deployer()

    # fetch existing services with same pipeline name, step name and model name
    existing_services = model_deployer.find_model_server(
        pipeline_name=pipeline_name,
        pipeline_step_name=pipeline_step_name,
        model_name=model_name,
        running=running,
    )

    if not existing_services:
        raise RuntimeError(
            f"No Hugging Face inference endpoint deployed by step "
            f"'{pipeline_step_name}' in pipeline '{pipeline_name}' with name "
            f"'{model_name}' is currently running."
        )

    return existing_services[0]


# Use the service for inference
@step
def predictor(
    service: HuggingFaceDeploymentService,
    data: str
) -> Annotated[str, "predictions"]:
    """Run a inference request against a prediction service"""

    prediction = service.predict(data)
    return prediction


@pipeline
def huggingface_deployment_inference_pipeline(
    pipeline_name: str, pipeline_step_name: str = "huggingface_model_deployer_step",
):
    inference_data = ...
    model_deployment_service = prediction_service_loader(
        pipeline_name=pipeline_name,
        pipeline_step_name=pipeline_step_name,
    )
    predictions = predictor(model_deployment_service, inference_data)
```

For more information and a full list of configurable attributes of the Hugging Face Model Deployer, check out the [SDK Docs](https://sdkdocs.zenml.io/latest/integration\_code\_docs/integrations-huggingface/#zenml.integrations.huggingface.model\_deployers).

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>