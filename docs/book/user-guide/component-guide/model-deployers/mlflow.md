---
description: Deploying your models locally with MLflow.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
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

### How do you use it?

The first step to being able to deploy and use your MLflow model is to create Service deployment from code, this is done
by setting the different parameters that the MLflow deployment step requires.

```python
from zenml.integrations.mlflow.steps import mlflow_deployer_step
from zenml.integrations.mlflow.steps import MLFlowDeployerParameters

...

model_deployer = mlflow_deployer_step(name="model_deployer")

...

# Initialize a continuous deployment pipeline run
deployment = continuous_deployment_pipeline(
    ...,
    # as a last step to our pipeline the model deployer step is run with it config in place
    model_deployer=model_deployer(params=MLFlowDeployerParameters(workers=3)),
)
```

You can run predictions on the deployed model with something like:

```python
from zenml.integrations.mlflow.services import MLFlowDeploymentService
from zenml.steps import BaseParameters, Output, StepContext, step
from zenml.services.utils import load_last_service_from_step

...


class MLFlowDeploymentLoaderStepParams(BaseParameters):
    """MLflow deployment getter configuration.

    Attributes:
        pipeline_name: name of the pipeline that deployed the MLflow prediction
            server
        step_name: the name of the step that deployed the MLflow prediction
            server
        running: when this flag is set, the step only returns a running service
    """

    pipeline_name: str
    step_name: str
    running: bool = True
    ...


# Step to retrieve the service associated with the last pipeline run
@step(enable_cache=False)
def prediction_service_loader(
        params: MLFlowDeploymentLoaderStepParams, context: StepContext
) -> MLFlowDeploymentService:
    """Get the prediction service started by the deployment pipeline"""

    service = load_last_service_from_step(
        pipeline_name=params.pipeline_name,
        step_name=params.step_name,
        running=params.running,
    )
    if not service:
        raise RuntimeError(
            f"No MLflow prediction service deployed by the "
            f"{params.step_name} step in the {params.pipeline_name} pipeline "
            f"is currently running."
        )

    return service


# Use the service for inference
@step
def predictor(
        service: MLFlowDeploymentService,
        data: np.ndarray,
) -> Output(predictions=np.ndarray):
    """Run a inference request against a prediction service"""

    service.start(timeout=10)  # should be a NOP if already started
    prediction = service.predict(data)
    prediction = prediction.argmax(axis=-1)

    return prediction


# Initialize an inference pipeline run
inference = inference_pipeline(
    ...,
    prediction_service_loader=prediction_service_loader(
        MLFlowDeploymentLoaderStepParams(
            pipeline_name="continuous_deployment_pipeline",
            step_name="model_deployer",
        )
    ),
    predictor=predictor(),
)
```

You can check the MLflow deployment example for more details.

* [Model Deployer with MLflow](https://github.com/zenml-io/zenml/tree/main/examples/mlflow\_deployment)

For more information and a full list of configurable attributes of the MLflow Model Deployer, check out
the [API Docs](https://apidocs.zenml.io/latest/integration\_code\_docs/integrations-mlflow/#zenml.integrations.mlflow.model\_deployers)
.
