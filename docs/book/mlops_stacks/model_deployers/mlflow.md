---
description: Deploy and Test your models locally with MLFlow
---

The MLFLow Model Deployer is one of the available flavors of the [Model Deployer](./overview.md) 
stack component. Provided with the MLFLow integration it can be used to deploy
and manage [MLFlow models](https://www.mlflow.org/docs/latest/python_api/mlflow.deployments.html) on a local running MLFlow server.

## When would you want to use it?

MLFlow is a popular open source platform for machine learning. It's a great tool for
managing the entire lifecycle of your machine learning. One of the most important features
of MLFlow is the ability to package your model and its dependencies into a single artifact
that can be deployed to a variety of deployment targets.

You should use the MLflow Model Deployer:

* if you want to have an easy way to deploy your models locally and perform real-time predictions using the running MLflow prediction server.

* if you are looking to deploy your models in a simple way without the need for a dedicated
  deployment environment like Kubernetes or advanced infrastructure configuration.

If you are looking to deploy your models in a more complex way, you should use one of the
other [Model Deployer Flavors]() available in ZenML (e.g. Seldon Core, KServe, etc.)

## How do you deploy it?

The MLflow Model Deployer flavor is provided by the MLflow ZenML integration, you need to install it on your local machine to be able to deploy your models. You can do this by running the following command:

```bash
zenml integration install mlflow -y
```

To register the MLFlow model deployer with ZenML you need to run the following command:

```bash
zenml model-deployer register mlflow_deployer --flavor=mlflow
```

The ZenML integration will provision a local MLflow deployment server as a daemon process that will continue to run in the background to serve the latest MLflow model.

## How do you use it?

The first step to be able to deploy and use your MLflow model is to create Service deployment from code, this is done by setting the different paramters that mlflow deployment step requires.

```python
from zenml.steps import BaseStepConfig
from zenml.integrations.mlflow.steps import mlflow_deployer_step
from zenml.integrations.mlflow.steps import MLFlowDeployerConfig

...

class MLFlowDeploymentLoaderStepConfig(BaseStepConfig):
    """MLflow deployment getter configuration

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
    
model_deployer = mlflow_deployer_step(name="model_deployer")

...

# Initialize a continuous deployment pipeline run
deployment = continuous_deployment_pipeline(
    ...,
    # as a last step to our pipeline the model deployer step is run with it config in place
    model_deployer=model_deployer(config=MLFlowDeployerConfig(workers=3)),
)
```

You can run predictions on the deployed model with something like:

```python
from zenml.integrations.mlflow.services import MLFlowDeploymentService
from zenml.steps import BaseStepConfig, Output, StepContext, step
from zenml.services import load_last_service_from_step

...

class MLFlowDeploymentLoaderStepConfig(BaseStepConfig):
    # see implementation above
    ...

# Step to retrieve the service associated with the last pipeline run
@step(enable_cache=False)
def prediction_service_loader(
    config: MLFlowDeploymentLoaderStepConfig, context: StepContext
) -> MLFlowDeploymentService:
    """Get the prediction service started by the deployment pipeline"""

    service = load_last_service_from_step(
        pipeline_name=config.pipeline_name,
        step_name=config.step_name,
        step_context=context,
        running=config.running,
    )
    if not service:
        raise RuntimeError(
            f"No MLflow prediction service deployed by the "
            f"{config.step_name} step in the {config.pipeline_name} pipeline "
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
        MLFlowDeploymentLoaderStepConfig(
            pipeline_name="continuous_deployment_pipeline",
            step_name="model_deployer",
        )
    ),
    predictor=predictor(),
)
```

You can check the MLFlow deployment example for more details.

- [Model Deployer with MLflow](https://github.com/zenml-io/zenml/tree/main/examples/mlflow_deployment)

For more information and a full list of configurable attributes of the MLFlow Model Deployer, check out the 
[API Docs](https://apidocs.zenml.io/latest/api_docs/integrations/#zenml.integrations.mlflow.model_deployers).