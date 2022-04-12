# ZenML continuous model deployment with MLflow deployments

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

## Overview

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

You can control which pipeline to run by passing the `--deploy` and/or the
`--predict` flag to the `run.py` launcher.

In the deployment pipeline, ZenML's MLflow tracking integration is used to log
the hyperparameter values -- as well as the trained model itself and the model
evaluation metrics -- as MLflow experiment tracking artifacts into the local
MLflow backend. This pipeline also launches a local MLflow deployment server
to serve the latest MLflow model if its accuracy is above a configured threshold.

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

## Run it locally

### Pre-requisites
In order to run this example, you need to install and initialize ZenML:

```shell
# install CLI
pip install zenml

# install ZenML integrations
zenml integration install mlflow tensorflow

# pull example
zenml example pull mlflow_deployment
cd zenml_examples/mlflow_deployment

# initialize
zenml init
```
### Setting up the ZenML Stack

The example can only be executed with a ZenML stack that has an MLflow model
deployer as a component. Configuring a new stack with a MLflow model deployer
could look like this:

```
zenml integration install mlflow
zenml model-deployer register mlflow --type=mlflow
zenml stack register local_with_mlflow -m default -a default -o default -d mlflow
zenml stack set local_with_mlflow
```

### Run the project
To run the continuous deployment pipeline:

```shell
python run.py --deploy
```

Re-running the example with different hyperparameter values will re-train
the model and update the MLflow deployment server to serve the new model:

```shell
python run.py --deploy --epochs=10 --learning_rate=0.1
```

If the input argument values are not changed, the pipeline caching feature
will kick in and the model will not be re-trained and the MLflow
deployment server will not be updated with the new model. Similarly, if a new
model is trained in the deployment pipeline but the model accuracy doesn't
exceed the configured accuracy threshold, the new model will not be deployed.

The inference pipeline will use the currently running MLflow deployment server
to perform an online prediction. To run the inference pipeline:

```shell
python run.py --predict
```

The `zenml served-models list` CLI command can be run to list the active model servers:

```shell
$ zenml served-models list
┏━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━┓
┃ STATUS │ UUID                                 │ PIPELINE_NAME                  │ PIPELINE_STEP_NAME         │ MODEL_NAME ┃
┠────────┼──────────────────────────────────────┼────────────────────────────────┼────────────────────────────┼────────────┨
┃   ✅   │ 87980237-843f-414f-bf06-931f4da69e56 │ continuous_deployment_pipeline │ mlflow_model_deployer_step │ model      ┃
┗━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━┛
```

To get more information about a specific model server, such as the prediction URL,
the `zenml served-models describe <uuid>` CLI command can be run:

```shell
$ zenml served-models describe 87980237-843f-414f-bf06-931f4da69e56
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
┃ PIPELINE_RUN_ID        │ continuous_deployment_pipeline-12_Apr_22-22_05_32… ┃
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
$ zenml served-models get-url 87980237-843f-414f-bf06-931f4da69e56
  Prediction URL of Served Model 87980237-843f-414f-bf06-931f4da69e56 is:
  http://localhost:8001/invocations
```

Finally, a model server can be deleted with the `zenml served-models delete <uuid>`
CLI command:

```shell
$ zenml served-models delete 87980237-843f-414f-bf06-931f4da69e56
Model server MLFlowDeploymentService[87980237-843f-414f-bf06-931f4da69e56] 
(type: model-serving, flavor: mlflow) was deleted.
```
### Clean up

To stop any prediction servers running in the background, use the
`zenml model-server list` and `zenml model-server delete <uuid>` CLI commands.:

```shell
zenml served-models delete 8cbe671b-9fce-4394-a051-68e001f92765
```

Then delete the remaining ZenML references.

```shell
rm -rf zenml_examples
```
