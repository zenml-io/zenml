# 🚀 Local model deployment with MLflow deployments

The popular open-source MLflow platform is known primarily for its great
[experiment tracking and visualization](https://mlflow.org/docs/latest/tracking.html)
user experience. Among its many features, MLflow also provides a standard format
for packaging ML models and deploying them for real-time serving using a range
of deployment tools.

This example continues the story around the ZenML integration for MLflow experiment
tracking showcased in the [mlflow_tracking example](../mlflow_tracking) and adds
deploying MLflow models locally with its
[local built-in deployment server](https://mlflow.org/docs/latest/models.html#deploy-mlflow-models).

The integration that ZenML makes with MLflow deployments allows users to implement
continuous model deployment with minimal effort.

## 🗺 Overview

The example uses the
[Fashion-MNIST](https://github.com/zalandoresearch/fashion-mnist) dataset to
train a classifier using [Tensorflow (Keras)](https://www.tensorflow.org/) using different
hyperparameter values (epochs and learning rate) that can also be supplied as command line
arguments.

This example uses an MLflow setup that is based on the local filesystem as
orchestrator and artifact store. See the [MLflow
documentation](https://www.mlflow.org/docs/latest/tracking.html#scenario-1-mlflow-on-localhost)
for details.

The example consists of two individual pipelines:

  * a deployment pipeline that implements a continuous deployment workflow. It
  ingests and processes input data, trains a model and then (re)deploys the
  prediction server that serves the model if it meets some evaluation
  criteria
  * an inference pipeline that interacts with the prediction server deployed
  by the continuous deployment pipeline to get online predictions based on live
  data

In the deployment pipeline, ZenML's MLflow tracking integration is used to log
the hyperparameter values -- as well as the trained model itself and the model
evaluation metrics -- as MLflow experiment tracking artifacts into the local
MLflow backend. This pipeline also launches a local MLflow deployment server
to serve the latest MLflow model if its accuracy is above a configured threshold.

The MLflow deployment server is running locally as a daemon process that will
continue to run in the background after the example execution is complete.

The deployment pipeline has caching enabled to avoid re-training the model if
the training data and hyperparameter values don't change. When a new model is
trained that passes the accuracy threshold validation, the pipeline
automatically updates the currently running MLflow deployment server so that
the new model is being served instead of the old one.

The inference pipeline simulates loading data from a dynamic external source,
then uses that data to perform online predictions using the running MLflow
prediction server.

## 🧰 How the example is implemented
This example contains two very important aspects that should be highlighted.

### 🛠️ Service deployment from code

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

### ↩️ Prediction against deployed model

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

# 🖥 Run it locally

## ⏩ SuperQuick `mlflow` run

If you're really in a hurry and you want just to see this example pipeline run,
without wanting to fiddle around with all the individual installation and
configuration steps, just run the following:

```shell
zenml example run mlflow_deployment
```

## 👣 Step-by-Step
### 📄 Prerequisites 
In order to run this example, you need to install and initialize ZenML:

```shell
# install CLI
pip install zenml

# install ZenML integrations
zenml integration install mlflow
zenml integration install tensorflow

# pull example
zenml example pull mlflow_deployment
cd zenml_examples/mlflow_deployment

# initialize
zenml init
```

### ▶️ Run the Code
To run the pipeline locally:

```shell
python run.py
```

Re-running the example with different hyperparameter values will re-train
the model and update the MLflow deployment server to serve the new model:

```shell
python run.py --epochs=10 --learning_rate=0.1
```

If the input argument values are not changed, the pipeline caching feature
will kick in and the model will not be re-trained. The inference pipeline
will use the currently running MLflow deployment server to perform an
online prediction.

Similarly, if a new model is trained in the deployment pipeline but the
model accuracy doesn't exceed the configured accuracy threshold, the new
model will not be deployed:

```shell
python run.py --epochs=1
```

Finally, to stop the prediction server, simply pass the `--stop-service` flag
to the example script:

```shell
python run.py --stop-service
```

### 🧽 Clean up
To stop the prediction server running in the background, pass the
`--stop-service` flag to the example script:

```shell
python run.py --stop-service
```

Then delete the remaining ZenML references.

```shell
rm -rf zenml_examples
```

# 📜 Learn more

Our docs regarding the mlflow deployment integration can be found [here](TODO: Link to docs).

If you want to learn more about deployment in zenml in general or about how to build your own deployer steps in zenml
check out our [docs](TODO: Link to docs)
