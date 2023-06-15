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

The example uses the [MNIST-digits](https://keras.io/api/datasets/mnist/) 
dataset to train a classifier using [Tensorflow (Keras)](https://www.tensorflow.org/) 
using different hyperparameter values (epochs and learning rate) that can also 
be supplied as command line arguments.

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

You can control which pipeline to run by passing the `--deploy` and/or the
`--predict` flag to the `run.py` launcher.

In the deployment pipeline, ZenML's MLflow tracking integration is used to log
the hyperparameter values -- as well as the trained model itself and the model
evaluation metrics -- as MLflow experiment tracking artifacts into the local
MLflow backend. This pipeline also launches a local MLflow deployment server
to serve the latest MLflow model if its accuracy is above a configured 
threshold.

The MLflow deployment server is running locally as a daemon process that will
continue to run in the background after the example execution is complete.
Subsequent runs of the deployment pipeline will restart the existing deployment
server to serve the more recent model version.

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
from zenml.steps import BaseParameters
from zenml.integrations.mlflow.steps import mlflow_deployer_step
from zenml.integrations.mlflow.steps import MLFlowDeployerParameters

...

class MLFlowDeploymentLoaderStepParameters(BaseParameters):
    """MLflow deployment getter parameters

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
    model_deployer=model_deployer(params=MLFlowDeployerParameters(workers=3)),
)
```

### ↩️ Prediction against deployed model

```python
from zenml import step
from zenml.integrations.mlflow.services import MLFlowDeploymentService
from zenml.steps import BaseParameters, Output, StepContext
from zenml.services import load_last_service_from_step

...

class MLFlowDeploymentLoaderStepParameters(BaseParameters):
    # see implementation above
    ...

# Step to retrieve the service associated with the last pipeline run
@step(enable_cache=False)
def prediction_service_loader(
    params: MLFlowDeploymentLoaderStepParameters
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

    service.start(timeout=60)  # should be a NOP if already started
    prediction = service.predict(data)
    prediction = prediction.argmax(axis=-1)

    return prediction

# Initialize an inference pipeline run
inference = inference_pipeline(
    ...,
    prediction_service_loader=prediction_service_loader(
        MLFlowDeploymentLoaderStepParameters(
            pipeline_name="continuous_deployment_pipeline",
            step_name="model_deployer",
        )
    ),
    predictor=predictor(),
)
```

# 🖥 Run it locally

## ⏩ SuperQuick `mlflow` run

If you're really in a hurry and just want to see this example pipeline run
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
pip install "zenml[server]"

# install ZenML integrations
zenml integration install mlflow tensorflow

# pull example
zenml example pull mlflow_deployment
cd zenml_examples/mlflow_deployment

# initialize
zenml init

# Start the ZenServer to enable dashboard access
zenml up
```
### 🥞 Setting up the ZenML Stack

The example can only be executed with a ZenML stack that has MLflow model
deployer and MLflow experiment tracker components. Configuring a new stack 
could look like this:

```
zenml integration install mlflow
zenml model-deployer register mlflow_deployer --flavor=mlflow
zenml experiment-tracker register mlflow_tracker --flavor=mlflow
zenml stack register local_mlflow_stack \
  -a default \
  -o default \
  -d mlflow_deployer \
  -e mlflow_tracker \
  --set
```

### ▶️ Run the Code
To run the continuous deployment pipeline:

```shell
python run.py --config deploy
```

Re-running the example with different hyperparameter values will re-train
the model and update the MLflow deployment server to serve the new model:

```shell
python run.py --config deploy --epochs=10 --lr=0.1
```

If the input argument values are not changed, the pipeline caching feature
will kick in and the model will not be re-trained and the MLflow
deployment server will not be updated with the new model. Similarly, if a new
model is trained in the deployment pipeline but the model accuracy doesn't
exceed the configured accuracy threshold, the new model will not be deployed.

The inference pipeline will use the currently running MLflow deployment server
to perform an online prediction. To run the inference pipeline:

```shell
python run.py --config predict
```

The `zenml model-deployer models list` CLI command can be run to list the active model servers:

```
$ zenml model-deployer models list
┏━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━┓
┃ STATUS │ UUID                                 │ PIPELINE_NAME                  │ PIPELINE_STEP_NAME         │ MODEL_NAME ┃
┠────────┼──────────────────────────────────────┼────────────────────────────────┼────────────────────────────┼────────────┨
┃   ✅   │ 87980237-843f-414f-bf06-931f4da69e56 │ continuous_deployment_pipeline │ mlflow_model_deployer_step │ model      ┃
┗━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━┛
```

To get more information about a specific model server, such as the prediction URL,
the `zenml model-deployer models describe <uuid>` CLI command can be run:

```
$ zenml model-deployer models describe 87980237-843f-414f-bf06-931f4da69e56
        Properties of Served Model 87980237-843f-414f-bf06-931f4da69e56        
┏━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ MODEL SERVICE PROPERTY │ VALUE                                              ┃
┠────────────────────────┼────────────────────────────────────────────────────┨
┃ DAEMON_PID             │ 105590                                             ┃
┠────────────────────────┼────────────────────────────────────────────────────┨
┃ MODEL_NAME             │ model                                              ┃
┠────────────────────────┼────────────────────────────────────────────────────┨
┃ MODEL_URI              │ file:///home/stefan/.config/zenml/local_stores/fd… ┃
┠────────────────────────┼────────────────────────────────────────────────────┨
┃ PIPELINE_NAME          │ continuous_deployment_pipeline                     ┃
┠────────────────────────┼────────────────────────────────────────────────────┨
┃ RUN_NAME               │ continuous_deployment_pipeline-12_Apr_22-22_05_32… ┃
┠────────────────────────┼────────────────────────────────────────────────────┨
┃ PIPELINE_STEP_NAME     │ mlflow_model_deployer_step                         ┃
┠────────────────────────┼────────────────────────────────────────────────────┨
┃ PREDICTION_URL         │ http://localhost:8001/invocations                  ┃
┠────────────────────────┼────────────────────────────────────────────────────┨
┃ SERVICE_PATH           │ /home/stefan/.config/zenml/local_stores/3b114be0-… ┃
┠────────────────────────┼────────────────────────────────────────────────────┨
┃ STATUS                 │ ✅                                                 ┃
┠────────────────────────┼────────────────────────────────────────────────────┨
┃ STATUS_MESSAGE         │ service daemon is not running                      ┃
┠────────────────────────┼────────────────────────────────────────────────────┨
┃ UUID                   │ 87980237-843f-414f-bf06-931f4da69e56               ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

The prediction URL can sometimes be more difficult to make out in the detailed
output, so there is a separate CLI command available to retrieve it:

```shell
$ zenml model-deployer models get-url 87980237-843f-414f-bf06-931f4da69e56
  Prediction URL of Served Model 87980237-843f-414f-bf06-931f4da69e56 is:
  http://localhost:8001/invocations
```

Finally, a model server can be deleted with the `zenml model-deployer models delete <uuid>`
CLI command:

```shell
$ zenml model-deployer models delete 87980237-843f-414f-bf06-931f4da69e56
Model server MLFlowDeploymentService[87980237-843f-414f-bf06-931f4da69e56] 
(type: model-serving, flavor: mlflow) was deleted.
```

### 🧽 Clean up

To stop any prediction servers running in the background, use the
`zenml model-server list` and `zenml model-server delete <uuid>` CLI commands.:

```shell
zenml model-deployer models delete 8cbe671b-9fce-4394-a051-68e001f92765
```

Then delete the remaining ZenML references.

```shell
rm -rf zenml_examples
```

# 📜 Learn more

Our docs regarding the MLflow deployment integration can be found 
[here](https://docs.zenml.io/component-gallery/model-deployers/mlflow).

If you want to learn more about deployment in ZenML in general or about how to 
build your own deployer steps in ZenML check out our 
[docs](https://docs.zenml.io/component-gallery/model-deployers/custom).
