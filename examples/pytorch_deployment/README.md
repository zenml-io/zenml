# ZenML continuous model deployment with Seldon Core

[Seldon Core](https://github.com/SeldonIO/seldon-core) is a production grade
open source model serving platform. It packs a wide range of features built
around deploying models to REST/GRPC microservices that include monitoring and
logging, model explainers, outlier detectors and various continuous deployment
strategies such as A/B testing, canary deployments and more.

Seldon Core also comes equipped with a set of built-in model server implementations 
for packaging ML models which greatly simplify the process of serving models for 
real-time inference.  
These built-in model servers are designed to work with some standard formats like tensorflow, sklearn, etc.

On top of these, Seldom Core also allows to deploy custom models when the 
use-case is not covered by Seldon pre-packaged inference servers. and This 
is possible by leveraging Seldon language wrappers to containerize 
the machine learning models and logic.

The following example demonstrates how we can build pipeline 
that train, evaluate and finally serve Pytorch model which require some pre-transformation with Seldon Core.


After [serving models locally with MLflow](../mlflow_deployment), switching to
a ZenML MLOps stack that features Seldon Core as a model deployer component
makes for a seamless transition from running experiments locally to deploying
models in production.
But sometimes the standard [model deployment with Seldon Core](../seldon_deployment)
is not enough either because our model flavor is not supported by the seldon 
pre-packaged servers or we need extra custom processing operations before or after
the prediction. 

## Overview

The example uses the [MNIST](http://yann.lecun.com/exdb/mnist/) dataset (originally developed by Yann LeCun and others) to train a classifier using [PyTorch](https://pytorch.org/). 
Different hyperparameter values (e.g. the number of epochs, batch size, learning rate and momentum value for the Pytorch model) can be supplied as command line arguments to the `run.py` Python script.

The example consists of an individual pipeline with and User defined Class:

  * a deployment pipeline that implements a continuous deployment workflow. It
  ingests and processes input data, trains a model and then (re)deploys the
  prediction server that serves the model if it meets some evaluation
  criteria
  * User defined class that inherits from ZenMLCustomModel which implements
  load and predict functions. (extra functions could be added to the class)

You can control which pipeline to run by passing the `--deploy` and/or the
`--predict` flag to the `run.py` launcher.

When running the deployment pipeline, ZenML wraps everything within the working directory
in a docker image with needed requirements, and pushes it to the active container
regitry. ZenML's Seldon Core integration then is used to prepare a Seldon deployment 
definition with the custom docker image, which was created for this pipeline, 
and the trained model. 
The trained model is loaded from the Artifact Store where it is automatically saved
as an artifact by the training step. A Seldon Core deployment server is launched to 
serve the latest model version if its accuracy is above a configured threshold 
(also customizable through a command line argument).

The Seldon Core deployment server is provisioned remotely as a Kubernetes
resource that continues to run after the deployment pipeline run is complete.
Subsequent runs of the deployment pipeline will reuse the existing deployment
server and merely update it to serve the more recent model version.

The deployment pipeline has caching enabled to avoid re-training and
re-deploying the model if the training data and hyperparameter values don't
change. When a new model is trained that passes the accuracy threshold
validation, the pipeline automatically updates the currently running Seldon Core
deployment server so that the new model is being served instead of the old one.

## Running the example

### Pre-requisites

For the ZenML Seldon Core custom deployer to work, four basic things are required:

1. access to a Kubernetes cluster. The example accepts a `--kubernetes-context`
command line argument. This Kubernetes context needs to point to the Kubernetes
cluster where Seldon Core model servers will be deployed. If the context is not
explicitly supplied to the example, it defaults to using the locally active
context.

2. Seldon Core needs to be preinstalled and running in the target Kubernetes
cluster (read below for a brief explanation of how to do that).

3. models deployed with Seldon Core need to be stored in some form of
persistent shared storage that is accessible from the Kubernetes cluster where
Seldon Core is installed (e.g. AWS S3, GCS, Azure Blob Storage, etc.).

4. Remote container registry in the active stack that is 
accessible from the Kubernetes cluster where Seldon Core is installed.

In order to run this example, you need to install and initialize ZenML:

```shell
# install CLI
pip install zenml

# install ZenML integrations
zenml integration install pytorch seldon

# install additional requirments
pip install torchvision

# pull example
zenml example pull seldon_custom_pytorch_deployment
cd zenml_examples/seldon_custom_pytorch_deployment

# initialize a local ZenML Repository
zenml init
```

#### Installing Seldon Core (e.g. in an GKE cluster)

This section is a trimmed up version of the
[official Seldon Core installation instructions](https://github.com/SeldonIO/seldon-core/tree/master/examples/auth#demo-setup)
applied to a particular type of Kubernetes cluster, GKE in this case. It assumes
that an GKE cluster is already set up and configured with IAM access.
For more informations about configurate access to GKE locally  
[Install kubectl and configure cluster access](https://cloud.google.com/kubernetes-engine/docs/how-to/cluster-access-for-kubectl)

To view the list of contexts for kubectl, run the following command

```bash
kubectl config current-context
```

Install Istio 1.5.0 (required for the latest Seldon Core version):

```bash
curl -L [https://istio.io/downloadIstio](https://istio.io/downloadIstio) | ISTIO_VERSION=1.5.0 sh -
cd istio-1.5.0/
bin/istioctl manifest apply --set profile=demo
```

Set up an Istio gateway for Seldon Core:

```bash
curl https://raw.githubusercontent.com/SeldonIO/seldon-core/master/notebooks/resources/seldon-gateway.yaml | kubectl apply -f -
```

Finally, install Seldon Core:

```bash
helm install seldon-core seldon-core-operator \
    --repo https://storage.googleapis.com/seldon-charts \
    --set usageMetrics.enabled=true \
    --set istio.enabled=true \
    --namespace seldon-system
```

To test that the installation is functional, you can use this sample Seldon
deployment:

```yaml
apiVersion: machinelearning.seldon.io/v1
kind: SeldonDeployment
metadata:
  name: iris-model
  namespace: default
spec:
  name: iris
  predictors:
  - graph:
      implementation: SKLEARN_SERVER
      modelUri: gs://seldon-models/v1.14.0-dev/sklearn/iris
      name: classifier
    name: default
    replicas: 1
```

```bash
kubectl apply -f iris.yaml
```

Extract the URL where the model server exposes its prediction API:

```bash
export INGRESS_HOST=$(kubectl -n istio-system get service istio-ingressgateway -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
```

Use curl to send a test prediction API request to the server:

```bash
curl -X POST http://$INGRESS_HOST/seldon/default/iris-model/api/v1.0/predictions \
         -H 'Content-Type: application/json' \
         -d '{ "data": { "ndarray": [[1,2,3,4]] } }'
```

You should see something like this as the prediction response:

```json
{"data":{"names":["t:0","t:1","t:2"],"ndarray":[[0.0006985194531162835,0.00366803903943666,0.995633441507447]]},"meta":{"requestPath":{"classifier":"seldonio/sklearnserver:1.13.1"}}}
```

### Setting up the ZenML Stack

Before you run the example, a ZenML Stack needs to be set up with all the proper
components. Two different examples of stacks featuring GCP infrastructure
components are described in this document, but similar stacks may be set up
using different backends and used to run the example as long as the basic Stack
prerequisites are met.

#### Local orchestrator with gcp artifact store and GKE Seldon Core installation

This stack consists of the following components:

* an GCP artifact store
* the local orchestrator
* the local metadata store
* a GCP container registry (artifact registry)
* a Seldon Core model deployer

To have access to the GCP artifact store and container registry from your local workstation, the the Google Cloud CLI needs to be intialized and authorized locally as documented in
[the official GCP documentation](https://cloud.google.com/sdk/docs/initializing).

In addition to the stack components, Seldon Core must be installed in a
Kubernetes cluster that is locally accessible through a Kubernetes configuration
context. The reference used in this example is a Seldon Core installation
running in an EKS cluster, but any other type of Kubernetes cluster can be used,
managed or otherwise.

For more informations about configurate access to GKE locally  
[Install kubectl and configure cluster access](https://cloud.google.com/kubernetes-engine/docs/how-to/cluster-access-for-kubectl)

To view the list of contexts for kubectl, run the following command

```bash
kubectl config current-context
```

Set up a namespace for ZenML Seldon Core workloads:

```bash
kubectl create ns zenml-workloads
```

Extract the URL where the Seldon Core model server exposes its prediction API, e.g.:

```bash
export INGRESS_HOST=$(kubectl -n istio-system get service istio-ingressgateway -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
```

Give Seldon Core access to the GCP artifact store in the configured namespace.
For this we need first to create a service-account key and have it as local json file. First make sure that you have [SA-NAME]@[PROJECT-ID].iam.gserviceaccount.com service account created in the gcloud console that have sufficient permissions to access the bucket where model will be stored (i.e. Storage Object Admin).

Generate the service-account key using gcloud.
```bash
gcloud iam service-accounts keys create gcloud-application-credentials.json --iam-account [SA-NAME]@[PROJECT-ID].iam.gserviceaccount.com
```

Give Seldon Core access to the GCP artifact store in the zenml-workloads namespace:

```bash
kubectl -n zenml-workloads create secret generic seldon-rclone-secret \
    --from-literal=RCLONE_CONFIG_GS_TYPE='google cloud storage' \
    --from-literal=RCLONE_CONFIG_GS_ANONYMOUS='false' \
    --from-literal=RCLONE_CONFIG_GS_SERVICE_ACCOUNT_CREDENTIALS="$(cat <path-to-json-key>)"
```

The name of the created secret also needs to be passed to the `run.py` example
launcher script via its `--secret` command line argument.

NOTE: this is based on the assumption that Seldon Core is running in an GKE
cluster that runs in the same project where container regsitry is defined otherwise
the permission should be granted to GKE instances to access the registry. 
More informations can be found at 
[the official GCP documentation](https://cloud.google.com/artifact-registry/docs/integrate-gke)

Configuring the stack can be done like this:

```
zenml integration install gcp seldon
zenml model-deployer register seldon_gcp --type=seldon \
  --kubernetes_context=gke_cluster-1 --kubernetes_namespace=zenml-workloads \
  --base_url=http://34.139.128.148
zenml artifact-store register gcp --type gcp --path gs://mybucket
zenml container-registry register gcp_registry --type=default --uri=gcr.io/container-registry
zenml stack register gcp_stack_seldon -m default -a gcp -o default -d seldon_gcp -c gcp_registry
zenml stack set gcp_stack_seldon
```

#### Full GCP stack

This stack has all components running in the GCP cloud:

* an GCP artifact store
* a Kubeflow orchestrator installed in an AWS EKS Kubernetes cluster
* a metadata store that uses the same database as the Kubeflow deployment as
a backend
* an GCP container registry (artifact registry)

To have access to the GCP artifact store and container registry from your local workstation, the the Google Cloud CLI needs to be intialized and authorized locally as documented in
[the official GCP documentation](https://cloud.google.com/sdk/docs/initializing).

In addition to the stack components, Seldon Core must be installed in *the same*
Kubernetes cluster as Kubeflow. The cluster must also be locally accessible
through a Kubernetes configuration context. The reference used in this example
is a Kubeflow and Seldon Core installation running in an GKE cluster, but any
other type of Kubernetes cluster can be used, managed or otherwise.

For more informations about configurate access to GKE locally  
[Install kubectl and configure cluster access](https://cloud.google.com/kubernetes-engine/docs/how-to/cluster-access-for-kubectl)

To view the list of contexts for kubectl, run the following command

```bash
kubectl config current-context
```

To configure GCP container registry access locally, run e.g.:

```bash
gcloud auth configure-docker
```

Extract the URL where the Seldon Core model server exposes its prediction API, e.g.:

```bash
export INGRESS_HOST=$(kubectl -n istio-system get service istio-ingressgateway \
  -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
```

Give Seldon Core access to the GCP artifact store in the configured namespace.
For this we need first to create a service-account key and have it as local json file. First make sure that you have [SA-NAME]@[PROJECT-ID].iam.gserviceaccount.com service account created in the gcloud console that have sufficient permissions to access the bucket where model will be stored (i.e. Storage Object Admin).

Generate the service-account key using gcloud.
```bash
gcloud iam service-accounts keys create gcloud-application-credentials.json --iam-account [SA-NAME]@[PROJECT-ID].iam.gserviceaccount.com
```

Give Seldon Core access to the GCP artifact store in the zenml-kubeflow namespace:

```bash
kubectl -n kubeflow create secret generic seldon-rclone-secret \
    --from-literal=RCLONE_CONFIG_GS_TYPE='google cloud storage' \
    --from-literal=RCLONE_CONFIG_GS_ANONYMOUS='false' \
    --from-literal=RCLONE_CONFIG_GS_SERVICE_ACCOUNT_CREDENTIALS="$(cat <path-to-json-key>)"
```

The name of the created secret also needs to be passed to the `run.py` example
launcher script via its `--secret` command line argument.

NOTE: this is based on the assumption that Seldon Core is running in an GKE
cluster that runs in the same project where container regsitry is defined otherwise
the permission should be granted to GKE instances to access the registry. 
More informations can be found at 
[the official GCP documentation](https://cloud.google.com/artifact-registry/docs/integrate-gke)

Configuring the stack can be done like this:

```
zenml integration install gcp kubeflow seldon

zenml model-deployer register seldon_gcp --type=seldon \
  --kubernetes_context=gke_cluster-1 --kubernetes_namespace=kubeflow \
  --base_url=http://34.139.128.148
zenml artifact-store register gcp --type gcp --path gs://mybucket
zenml container-registry register gcp --type=default --uri=gcr.io/container-registry
zenml metadata-store register gcp --type=kubeflow
zenml orchestrator register gcp --type=kubeflow --kubernetes_context=gke_cluster-1 --synchronous=True
zenml stack register gcp_kubeflow_seldon -m gcp -a gcp -o gcp -d seldon_gcp -c gcp
zenml stack set gcp_kubeflow_seldon

```

### Run the project
To run the continuous deployment pipeline:

```shell
python run.py --secret seldon-rclone-secret --deploy
```

Example output when run with the local orchestrator stack:

```
zenml/seldon_deployment$ python run.py --secret seldon-rclone-secret --deploy --min-accuracy 0.80

Creating run for pipeline: `seldon_pytorch_deployment_pipeline`
Cache disabled for pipeline `seldon_pytorch_deployment_pipeline`
Using stack `gcp_stack_seldon` to run pipeline `seldon_pytorch_deployment_pipeline`...
Step `torch_trainer` has started.
Train Epoch: 1  Loss: 0.000048
Train Epoch: 2  Loss: 1.023394
Train Epoch: 3  Loss: 0.015611
Step `torch_trainer` has finished in 2m40s.
Step `torch_evaluator` has started.

Test set: Average loss: 0.0694, Accuracy: 9789/10000 (98%)

Step `torch_evaluator` has finished in 8.094s.
Step `deployment_trigger` has started.
Step `deployment_trigger` has finished in 3.724s.
Step `seldon_custom_model_deployer_step` has started.
No explicit dockerignore specified and no file called .dockerignore exists at the build context root (/Users/safoine-zenml/work-dir/zen/zenml/examples/seldon_custom_pytorch_deployment). Creating docker build context with all files inside the build context root directory.
Building docker image 'gcr.io/zenml-core/zenml-kubeflow/zenml-seldon-custom-deploy:seldon_pytorch_deployment_pipeline-seldon_custom_model_deployer_step', this might take a while...
Step 1/10 : FROM zenmldocker/zenml:latest

...

Successfully built 8f5c1bb57b69
Successfully tagged gcr.io/zenml-core/zenml-kubeflow/zenml-seldon-custom-deploy:seldon_pytorch_deployment_pipeline-seldon_custom_model_deployer_step
Finished building docker image.
Pushing docker image 'gcr.io/zenml-core/zenml-kubeflow/zenml-seldon-custom-deploy:seldon_pytorch_deployment_pipeline-seldon_custom_model_deployer_step'.
Finished pushing docker image.
Creating a new Seldon deployment service: SeldonDeploymentService[1fcafadd-e918-4170-a506-8c2224506044] (type: model-serving, flavor: seldon)
Seldon deployment service started and reachable at:
    http://104.155.117.93/seldon/zenml-workloads/zenml-1fcafadd-e918-4170-a506-8c2224506044/api/v0.1/predictions

Step `seldon_custom_model_deployer_step` has finished in 1m30s.
Pipeline run `seldon_pytorch_deployment_pipeline-21_Apr_22-13_10_16_626880` has finished in 4m23s.
The Seldon prediction server is running remotely as a Kubernetes service and accepts inference requests at:
    http://104.155.117.93/seldon/zenml-workloads/zenml-1fcafadd-e918-4170-a506-8c2224506044/api/v0.1/predictions
To stop the service, run `zenml served-models delete 1fcafadd-e918-4170-a506-8c2224506044`.
```

Re-running the example with different hyperparameter values will re-train
the model and update the deployment server to serve the new model:

```shell
python run.py --secret seldon-rclone-secret --deploy --epochs=5 --learning_rate=0.1
```

If the input hyperparameter argument values are not changed, the pipeline
caching feature will kick in, a new model will not be re-trained and the Seldon
Core deployment will not be updated with the new model. Similarly, if a new model
is trained in the deployment pipeline but the model accuracy doesn't exceed the
configured accuracy threshold, the new model will not be deployed.


The `zenml served-models list` CLI command can be run to list the active model servers:

```shell
$ zenml served-models list
┏━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━┓
┃ STATUS │ UUID                                 │ PIPELINE_NAME                      │ PIPELINE_STEP_NAME                │ MODEL_NAME ┃
┠────────┼──────────────────────────────────────┼────────────────────────────────────┼───────────────────────────────────┼────────────┨
┃   ✅   │ 1fcafadd-e918-4170-a506-8c2224506044 │ seldon_pytorch_deployment_pipeline │ seldon_custom_model_deployer_step │ mnist      ┃
┗━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━┛
```

To get more information about a specific model server, such as the prediction URL,
the `zenml served-models describe <uuid>` CLI command can be run:

```shell
$ zenml served-models describe 1fcafadd-e918-4170-a506-8c2224506044
                                     Properties of Served Model 1fcafadd-e918-4170-a506-8c2224506044                                     
┏━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ MODEL SERVICE PROPERTY │ VALUE                                                                                                        ┃
┠────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────────┨
┃ MODEL_NAME             │ mnist                                                                                                        ┃
┠────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────────┨
┃ MODEL_URI              │ gs://zenml-kubeflow-artifact-store/torch_trainer/output/664                                                  ┃
┠────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────────┨
┃ PIPELINE_NAME          │ seldon_pytorch_deployment_pipeline                                                                           ┃
┠────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────────┨
┃ PIPELINE_RUN_ID        │ seldon_pytorch_deployment_pipeline-21_Apr_22-13_10_16_626880                                                 ┃
┠────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────────┨
┃ PIPELINE_STEP_NAME     │ seldon_custom_model_deployer_step                                                                            ┃
┠────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────────┨
┃ PREDICTION_URL         │ http://104.155.117.93/seldon/zenml-workloads/zenml-1fcafadd-e918-4170-a506-8c2224506044/api/v0.1/predictions ┃
┠────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────────┨
┃ SELDON_DEPLOYMENT      │ zenml-1fcafadd-e918-4170-a506-8c2224506044                                                                   ┃
┠────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────────┨
┃ STATUS                 │ ✅                                                                                                           ┃
┠────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────────┨
┃ STATUS_MESSAGE         │ Seldon Core deployment 'zenml-1fcafadd-e918-4170-a506-8c2224506044' is available                             ┃
┠────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────────┨
┃ UUID                   │ 1fcafadd-e918-4170-a506-8c2224506044                                                                         ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

The prediction URL can sometimes be more difficult to make out in the detailed
output, so there is a separate CLI command available to retrieve it:

```shell
$ zenml served-models get-url 1fcafadd-e918-4170-a506-8c2224506044
  Prediction URL of Served Model 1fcafadd-e918-4170-a506-8c2224506044 is:
  http://104.155.117.93/seldon/zenml-workloads/zenml-1fcafadd-e918-4170-a506-8c2224506044/api/v0.1/predictions
```

Finally, a model server can be deleted with the `zenml served-models delete <uuid>`
CLI command:

```shell
$ zenml served-models delete 1fcafadd-e918-4170-a506-8c2224506044
Model server SeldonDeploymentService[1fcafadd-e918-4170-a506-8c2224506044] (type: model-serving, flavor: seldon) was deleted.
```

### Clean up

To stop any prediction servers running in the background, use the `zenml model-server list`
and `zenml model-server delete <uuid>` CLI commands.:

```shell
zenml served-models delete 1fcafadd-e918-4170-a506-8c2224506044
```

Then delete the remaining ZenML references.

```shell
rm -rf zenml_examples
```