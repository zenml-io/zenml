# 🚀 ZenML continuous model deployment with Seldon Core

[Seldon Core](https://github.com/SeldonIO/seldon-core) is a production grade
open source model serving platform. It packs a wide range of features built
around deploying models to REST/GRPC microservices that include monitoring and
logging, model explainers, outlier detectors and various continuous deployment
strategies such as A/B testing, canary deployments and more.

Seldon Core also comes equipped with a set of built-in model server
implementations designed to work with standard formats for packaging ML models
that greatly simplify the process of serving models for real-time inference.

This example demonstrates how easy it is to build a continuous deployment
pipeline that trains a model and then serves it with Seldon Core as the
industry-ready model deployment tool of choice.

After [serving models locally with MLflow](../mlflow_deployment), switching to
a ZenML MLOps stack that features Seldon Core as a model deployer component
makes for a seamless transition from running experiments locally to deploying
models in production.

## 🗺 Overview

The example uses the
[MNIST-digits](https://keras.io/api/datasets/mnist/) dataset to
train a classifier using either [Tensorflow (Keras)](https://www.tensorflow.org/)
or [scikit-learn](https://scikit-learn.org/stable/). Different
hyperparameter values (e.g. the number of epochs and learning rate for the Keras
model, solver and penalty for the scikit-learn logical regression) can be
supplied as command line arguments to the `run.py` Python script.

The example consists of two individual pipelines:

  * a deployment pipeline that implements a continuous deployment workflow. It
  ingests and processes input data, trains a model and then (re)deploys the
  prediction server that serves the model if it meets some evaluation
  criteria
  * an inference pipeline that interacts with the prediction server deployed
  by the continuous deployment pipeline to get online predictions based on live
  data

You can control which pipeline to run by passing the `--config deploy` or the 
`--config predict` option to the `run.py` launcher. The default is 
`--config deploy_and_predict` which does both.

In the deployment pipeline, ZenML's Seldon Core integration is used to serve
the trained model directly from the Artifact Store where it is automatically
saved as an artifact by the training step. A Seldon Core deployment server
is launched to serve the latest model version if its accuracy is above a
configured threshold (also customizable through a command line argument).

The Seldon Core deployment server is provisioned remotely as a Kubernetes
resource that continues to run after the deployment pipeline run is complete.
Subsequent runs of the deployment pipeline will reuse the existing deployment
server and merely update it to serve the more recent model version.

The deployment pipeline has caching enabled to avoid re-training and
re-deploying the model if the training data and hyperparameter values don't
change. When a new model is trained that passes the accuracy threshold
validation, the pipeline automatically updates the currently running Seldon Core
deployment server so that the new model is being served instead of the old one.

The inference pipeline simulates loading data from a dynamic external source,
then uses that data to perform online predictions using the running Seldon
Core prediction server.

# 🏠 Local Stack

## 📄 Infrastructure Requirements (Pre-requisites)

You don't need to set up any infrastructure to run your pipelines with Seldon, locally. However, you need the following tools installed:
  * Docker must be installed on your local machine.
  * Install k3d by running `curl -s https://raw.githubusercontent.com/rancher/k3d/main/install.sh | bash`.

You also need to be running Linux or Windows. MacOS is currently not supported
for these local deployments.

## Create a local Seldon Stack

To get a stack with Seldon Core and potential other components, you can make use of ZenML's Stack Recipes that are a set of terraform based modules that take care of setting up a cluster with Seldon among other things.

Run the following command to deploy the local Seldon stack:

```bash
zenml stack recipe deploy k3d-modular -d seldon
```

>**Note**:
> This recipe comes with MLflow, Kubeflow and Minio enabled by default. If you
> want any other components like Seldon or Tekton, you can specify that using
> the relevant flag (i.e. `-o` for orchestrators and so on).

This will deploy a local Kubernetes cluster with Seldon installed.
It will also generate a stack YAML file that you can import as a ZenML stack by running:

```bash
zenml stack import -f <path-to-stack-yaml>
```
Once the stack is set, you can then simply proceed to running your pipelines.

# ☁️ Cloud Stack

### 📄 Prerequisites 

In order to run this example, you need to install and initialize ZenML:

```shell
# install CLI
pip install "zenml[server]"

# install ZenML integrations
zenml integration install tensorflow sklearn seldon

# pull example
zenml example pull seldon_deployment
cd zenml_examples/seldon_deployment

# initialize a local ZenML Repository
zenml init

# Start the ZenServer to enable dashboard access
zenml up
```

For the ZenML Seldon Core deployer to work, three basic things are required:

1. access to a Kubernetes cluster. The example accepts a `--kubernetes-context`
command line argument. This Kubernetes context needs to point to the Kubernetes
cluster where Seldon Core model servers will be deployed. If the context is not
explicitly supplied to the example, it defaults to using the locally active
context.

2. Seldon Core needs to be preinstalled and running in the target Kubernetes
cluster (read below for a brief explanation of how to do that).

3. models deployed with Seldon Core are stored in the ZenML Artifact
Store that is used to train the models (e.g. Minio, AWS S3, GCS, Azure Blob
Storage, etc.). The Seldon Core model deployer needs to access the artifact
store to fetch the model artifacts, which means that it may need access to
credentials for the Artifact Store, unless Seldon Core is deployed in the
same cloud as the Artifact Store and is able to access it directly without
requiring explicit credentials, through some in-cloud provider specific
implicit authentication mechanism. For this reason, you may need to configure
your Artifact Store stack component with explicit credentials. See the
section [Local and remote authentication](#local-and-remote-authentication)
for more details.


#### Installing Seldon Core (e.g. in an EKS cluster)

This section is a trimmed up version of the
[official Seldon Core installation instructions](https://github.com/SeldonIO/seldon-core/tree/master/examples/auth#demo-setup)
applied to a particular type of Kubernetes cluster, EKS in this case. It assumes
that an EKS cluster is already set up and configured with IAM access.

To configure EKS cluster access locally, e.g:

```bash
aws eks --region us-east-1 update-kubeconfig --name zenml-cluster --alias zenml-eks
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
export INGRESS_HOST=$(kubectl -n istio-system get service istio-ingressgateway -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
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

### 🥞 Setting up the ZenML Stack

Before you run the example, a ZenML Stack needs to be set up with all the proper
components. Two different examples of stacks featuring AWS infrastructure
components are described in this document, but similar stacks may be set up
using different backends and used to run the example as long as the basic Stack
prerequisites are met.

#### Deploying Individual Stack Components using the CLI

The Seldon model deployer and the AWS S3 artifact store can be deployed using the ZenML CLI as well, using the `zenml
<STACK_COMPONENT> deploy` command. For more information on this `deploy`
subcommand, please refer to the
[documentation](https://docs.zenml.io/platform-guide/set-up-your-mlops-platform/deploy-and-set-up-a-cloud-stack/deploy-a-stack-component).

#### Local and remote authentication

The ZenML Stacks featured in this example are based on managed AWS services like
S3 storage, EKS Kubernetes and ECR container registry. In order to access these
services from your host, you need to have an AWS account and have the proper
credentials set up on your machine. The easiest way to do this is to install the
AWS CLI and set up AWS client credentials locally as documented in
[the official AWS documentation](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html).

In addition to local access, some stack components running remotely also need
to access AWS services. For example:

* the ZenML orchestrator (e.g. Kubeflow) needs to be able to access the AWS S3
bucket to store and retrieve pipeline run artifacts.
* the ZenML Seldon Core model deployer needs to be able to access the AWS S3 bucket
configured for the ZenML Artifact Store, because this is where models will be
stored and loaded from.

If the ZenML orchestrator and Seldon Core are already running in the AWS cloud (e.g.
in an EKS cluster), there are ways of configuring AWS workloads to have implicit
access to other AWS resources like S3 without requiring explicit credentials.
However, if either the ZenML Orchestrator or Seldon Core is running in a
different cloud, or on-prem, or if the AWS implicit in-cloud workload
authentication is not enabled, then explicit AWS credentials are required.

Concretely, this means that the S3 Artifact Store ZenML stack component needs to
be configured with explicit AWS credentials (i.e. an AWS access key and secret
key) that can also be used by other ZenML stack components like the ZenML
orchestrator and Seldon Core model deployer to access the bucket.

In the sections that follow, this is explained in more detail for the two
different examples of ZenML stacks featured in this document.

##### AWS Authentication with Implicit IAM Access

If the EKS cluster where Seldon Core is running already has
[IAM access](https://docs.aws.amazon.com/eks/latest/userguide/security-iam.html)
configured to grant the EKS nodes implicit access to the AWS S3 bucket,
you don't need to configure any explicit AWS credentials for the S3 Artifact
Store. The ZenML orchestrator and Seldon Core model deployer will automatically
default to using the environment authentication.

##### AWS Authentication with Explicit Credentials

If IAM access is not configured for your EKS cluster, or you don't know how to
configure it, you will need an explicit AWS access key and secret key that
grants access to the S3 bucket. To create an AWS access key and secret key,
follow the instructions in [the official AWS documentation](https://aws.amazon.com/premiumsupport/knowledge-center/create-access-key/). Please remember to grant the created IAM user permissions
to read and write to your S3 bucket (i.e. use the `AmazonS3FullAccess` policy).

When you have the AWS access key id and secret access key, you can configure a ZenML
secret to store them securely. You will reference the secret when you configure
the S3 Artifact Store stack component in the next sections:

```bash
zenml secret create s3-store \
   --aws_access_key_id=<YOUR-AWS-ACCESS-KEY-ID> \
   --aws_secret_access_key=<YOUR-AWS-SECRET-ACCESS-KEY>
```

This is how you would register a ZenML S3 Artifact Store with explicit
credentials referencing the secret you just created:

```bash
zenml artifact-store register aws --flavor=s3 --path s3://mybucket \
  --authentication_secret=s3_secret
```

#### Local orchestrator with S3 artifact store and EKS Seldon Core installation

This stack consists of the following components:

* an AWS S3 artifact store
* the local orchestrator
* a Seldon Core model deployer
* an image builder

In addition to the stack components, Seldon Core must be installed in a
Kubernetes cluster that is locally accessible through a Kubernetes configuration
context. The reference used in this example is a Seldon Core installation
running in an EKS cluster, but any other type of Kubernetes cluster can be used,
managed or otherwise.

To configure EKS cluster access locally, e.g:

```bash
aws eks --region us-east-1 update-kubeconfig --name zenml-cluster --alias zenml-eks
```

Set up a namespace for ZenML Seldon Core workloads:

```bash
kubectl create ns zenml-workloads
```

Extract the URL where the Seldon Core model server exposes its prediction API, e.g.:

```bash
export INGRESS_HOST=$(kubectl -n istio-system get service istio-ingressgateway -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
```

Configuring the stack can look as described below:

```bash
zenml integration install s3 seldon
zenml model-deployer register seldon_eks --flavor=seldon \
  --kubernetes_context=zenml-eks --kubernetes_namespace=zenml-workloads \
  --base_url=http://$INGRESS_HOST
zenml artifact-store register aws --flavor=s3 --path s3://mybucket
zenml image-builder register local_builder --flavor=local
zenml stack register local_with_aws_storage -a aws -o default -d seldon_eks -i local_builder --set
```

>**Note**:
> As already covered in the [Local and remote authentication](#local-and-remote-authentication) section, you will need to configure the Artifact Store with explicit credentials if IAM access is not configured for your EKS cluster:
> ```shell
> zenml artifact-store register aws --flavor=s3 --path s3://mybucket \
>   --authentication_secret=s3_secret
> ```

#### Full AWS stack

This stack has all components running in the AWS cloud:

* an AWS S3 artifact store
* a Kubeflow orchestrator installed in an AWS EKS Kubernetes cluster
* an AWS ECR container registry
* a Seldon Core model deployer pointing to the AWS EKS cluster

In order to run this example with a remote orchestrator such as Kubeflow, the 
first thing that you would require is a remote ZenML server deployed to the 
cloud. See the [deployment guide](https://docs.zenml.io/platform-guide/set-up-your-mlops-platform/deploy-zenml) 
for more information.

In addition to the stack components, Seldon Core must be installed in *the same*
Kubernetes cluster as Kubeflow. The cluster must also be locally accessible
through a Kubernetes configuration context. The reference used in this example
is a Kubeflow and Seldon Core installation running in an EKS cluster, but any
other type of Kubernetes cluster can be used, managed or otherwise.

To configure EKS cluster access locally, run e.g:

```bash
aws eks --region us-east-1 update-kubeconfig --name zenml-cluster --alias zenml-eks
```

To configure ECR registry access locally, run e.g.:

```bash
aws ecr get-login-password --region us-east-1 | docker login --username AWS \
  --password-stdin 715803424590.dkr.ecr.us-east-1.amazonaws.com
```

Extract the URL where the Seldon Core model server exposes its prediction API, e.g.:

```bash
export INGRESS_HOST=$(kubectl -n istio-system get service istio-ingressgateway \
  -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
```

Configuring the stack can look as described below:

```shell
zenml integration install s3 aws kubeflow seldon

zenml artifact-store register aws --flavor=s3 --path=s3://mybucket
zenml model-deployer register seldon_aws --flavor=seldon \
  --kubernetes_context=zenml-eks --kubernetes_namespace=kubeflow \
  --base_url=http://$INGRESS_HOST
zenml container-registry register aws --flavor=default --uri=715803424590.dkr.ecr.us-east-1.amazonaws.com
zenml orchestrator register aws --flavor=kubeflow --kubernetes_context=zenml-eks --synchronous=True
zenml image-builder register local_builder --flavor=local
zenml stack register aws -a aws -o aws -c aws -d seldon_aws -i local_builder --set
```

>**Note**:
> As already covered in the [Local and remote authentication](#local-and-remote-authentication) section, you will need to configure the Artifact Store with explicit credentials if IAM access is not configured for your EKS cluster:
> ```shell
> zenml artifact-store register aws --flavor=s3 --path s3://mybucket \
>   --authentication_secret=s3_secret
> ```

ZenML will manage the Seldon Core deployments inside the same `kubeflow`
namespace where the Kubeflow pipelines are running. You also have to update 
the set of permissions granted by Kubeflow to the Kubernetes service account 
in the context of which Kubeflow pipelines are running to allow the ZenML 
workloads to create, update and delete secrets. You can do so with the below 
command:

```bash
kubectl -n kubeflow patch role pipeline-runner --type='json' -p='[{"op": "add", "path": "/rules/0", "value": {"apiGroups": [""], "resources": ["secrets","serviceaccounts"], "verbs": ["*"]}}]'
```


### 🏃️Run the code
To run the continuous deployment pipeline:

```shell
python run.py --config deploy
```

Example output when run with the local orchestrator stack:

```shell
examples/seldon_deployment$ python run.py --config deploy --min-accuracy 0.80 --model-flavor sklearn
```

```shell
2022-04-06 15:40:28.903233: W tensorflow/stream_executor/platform/default/dso_loader.cc:64] Could not load dynamic library 'libcudart.so.11.0'; dlerror: libcudart.so.11.0: cannot open shared object file: No such file or directory
2022-04-06 15:40:28.903253: I tensorflow/stream_executor/cuda/cudart_stub.cc:29] Ignore above cudart dlerror if you do not have a GPU set up on your machine.
Creating run for pipeline: `continuous_deployment_pipeline`
Cache disabled for pipeline `continuous_deployment_pipeline`
Using stack `local_with_aws_storage` to run pipeline `continuous_deployment_pipeline`...
Step `importer_mnist` has started.
INFO:botocore.credentials:Found credentials in shared credentials file: ~/.aws/credentials
Step `importer_mnist` has finished in 20.012s.
Step `normalizer` has started.
Step `normalizer` has finished in 24.177s.
Step `sklearn_trainer` has started.
Step `sklearn_trainer` has finished in 23.150s.
Step `sklearn_evaluator` has started.
Step `sklearn_evaluator` has finished in 10.511s.
Step `deployment_trigger` has started.
Step `deployment_trigger` has finished in 4.965s.
Step `seldon_model_deployer` has started.
INFO:asyncio:Loading last service deployed by step model_deployer and pipeline continuous_deployment_pipeline...
Creating a new Seldon deployment service
Seldon deployment service started and reachable at:
    http://abb84c444c7804aa98fc8c097896479d-377673393.us-east-1.elb.amazonaws.com/seldon/zenml-workloads/zenml-1
6241824-7e17-42d8-bed3-070b51ba29d2/api/v0.1/predictions

Step `seldon_model_deployer` has finished in 39.095s.
Pipeline run `continuous_deployment_pipeline-06_Apr_22-15_40_31_886832` has finished in 2m2s.
The Seldon prediction server is running remotely as a Kubernetes service and accepts inference requests at:
    http://abb84c444c7804aa98fc8c097896479d-377673393.us-east-1.elb.amazonaws.com/seldon/zenml-workloads/zenml-1
6241824-7e17-42d8-bed3-070b51ba29d2/api/v0.1/predictions
To stop the service, re-run the same command and supply the `--stop-service` argument.
```

Example Kubeflow pipeline when run with the remote Kubeflow stack:

![Kubeflow Deployment Pipeline](assets/kubeflow-deployment.png)


Re-running the example with different hyperparameter values will re-train
the model and update the deployment server to serve the new model:

```shell
python run.py --config deploy --epochs=10 --lr=0.1
```

If the input hyperparameter argument values are not changed, the pipeline
caching feature will kick in, a new model will not be re-trained and the Seldon
Core deployment will not be updated with the new model. Similarly, if a new 
model is trained in the deployment pipeline but the model accuracy doesn't 
exceed the configured accuracy threshold, the new model will not be deployed.

The inference pipeline will use the currently running Seldon Core deployment
server to perform an online prediction. To run the inference pipeline:

```shell
python run.py --config predict
```

Example output when run with the local orchestrator stack:

```shell
examples/seldon_deployment$ python run.py --config predict --model-flavor sklearn
```

```shell
2022-04-06 15:48:02.346731: W tensorflow/stream_executor/platform/default/dso_loader.cc:64] Could not load dynamic library 'libcudart.so.11.0'; dlerror: libcudart.so.11.0: cannot open shared object file: No such file or directory
2022-04-06 15:48:02.346762: I tensorflow/stream_executor/cuda/cudart_stub.cc:29] Ignore above cudart dlerror if you do not have a GPU set up on your machine.
Creating run for pipeline: `inference_pipeline`
Cache disabled for pipeline `inference_pipeline`
Using stack `local_with_aws_storage` to run pipeline `inference_pipeline`...
Step `dynamic_importer` has started.
INFO:botocore.credentials:Found credentials in shared credentials file: ~/.aws/credentials
Step `dynamic_importer` has finished in 6.284s.
Step `prediction_service_loader` has started.
Step `prediction_service_loader` has finished in 7.104s.
Step `sklearn_predict_preprocessor` has started.
Step `sklearn_predict_preprocessor` has finished in 5.180s.
Step `predictor` has started.
Prediction:  [7 2 1 0 4 1 4 9 6 9 0 6 9 0 1 5 9 7 3 4 9 6 6 5 4 0 7 4 0 1 3 1 3 6 7 2 7
 1 2 1 1 7 4 2 3 5 1 2 4 4 6 3 5 5 6 0 4 1 9 5 7 8 9 2 7 4 7 4 3 0 7 0 2 9
 1 7 3 2 9 7 7 6 2 7 8 4 7 3 6 1 3 6 9 3 1 4 1 7 6 9]
Step `predictor` has finished in 8.009s.
Pipeline run `inference_pipeline-06_Apr_22-15_48_05_308089` has finished in 26.702s.
The Seldon prediction server is running remotely as a Kubernetes service and accepts inference requests at:
    http://abb84c444c7804aa98fc8c097896479d-377673393.us-east-1.elb.amazonaws.com/seldon/zenml-workloads/zenml-162
41824-7e17-42d8-bed3-070b51ba29d2/api/v0.1/predictions
To stop the service, re-run the same command and supply the `--stop-service` argument.
```

Example Kubeflow pipeline when run with the remote Kubeflow stack:

![Kubeflow Inference Pipeline](assets/kubeflow-prediction.png)

To switch from Tensorflow to sklearn as the libraries used for model
training and the Seldon Core model server implementation, the `--model-flavor`
command line argument can be used:

```
python run.py --model-flavor sklearn --penalty=l2
```

The `zenml model-deployer models list` CLI command can be run to list the active model servers:

```shell
$ zenml model-deployer models list
┏━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ STATUS │ UUID                                 │ PIPELINE_NAME                  │ PIPELINE_STEP_NAME         ┃
┠────────┼──────────────────────────────────────┼────────────────────────────────┼────────────────────────────┨
┃   ✅   │ 8cbe671b-9fce-4394-a051-68e001f92765 │ continuous_deployment_pipeline │ seldon_model_deployer_step ┃
┗━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

To get more information about a specific model server, such as the prediction URL,
the `zenml model-deployer models describe <uuid>` CLI command can be run:

```shell
$ zenml model-deployer models describe 8cbe671b-9fce-4394-a051-68e001f92765
                          Properties of Served Model 8cbe671b-9fce-4394-a051-68e001f92765                          
┏━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ MODEL SERVICE PROPERTY │ VALUE                                                                                  ┃
┠────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────┨
┃ MODEL_NAME             │ mnist                                                                                  ┃
┠────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────┨
┃ MODEL_URI              │ s3://zenprojects/seldon_model_deployer_step/output/884/seldon                          ┃
┠────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────┨
┃ PIPELINE_NAME          │ continuous_deployment_pipeline                                                         ┃
┠────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────┨
┃ RUN_NAME               │ continuous_deployment_pipeline-11_Apr_22-09_39_27_648527                               ┃
┠────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────┨
┃ PIPELINE_STEP_NAME     │ seldon_model_deployer_step                                                             ┃
┠────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────┨
┃ PREDICTION_URL         │ http://abb84c444c7804aa98fc8c097896479d-377673393.us-east-1.elb.amazonaws.com/seldon/… ┃
┠────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────┨
┃ SELDON_DEPLOYMENT      │ zenml-8cbe671b-9fce-4394-a051-68e001f92765                                             ┃
┠────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────┨
┃ STATUS                 │ ✅                                                                                     ┃
┠────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────┨
┃ STATUS_MESSAGE         │ Seldon Core deployment 'zenml-8cbe671b-9fce-4394-a051-68e001f92765' is available       ┃
┠────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────┨
┃ UUID                   │ 8cbe671b-9fce-4394-a051-68e001f92765                                                   ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

The prediction URL can sometimes be more difficult to make out in the detailed
output, so there is a separate CLI command available to retrieve it:

```shell
$ zenml model-deployer models get-url 8cbe671b-9fce-4394-a051-68e001f92765
  Prediction URL of Served Model 8cbe671b-9fce-4394-a051-68e001f92765 is:
  http://abb84c444c7804aa98fc8c097896479d-377673393.us-east-1.elb.amazonaws.com/seldon/zenml-workloads/zenml-8cbe67
1b-9fce-4394-a051-68e001f92765/api/v0.1/predictions
```

Finally, a model server can be deleted with the `zenml model-deployer models delete <uuid>`
CLI command:

```shell
$ zenml model-deployer models delete 8cbe671b-9fce-4394-a051-68e001f92765
```

### 🧽 Clean up

To stop any prediction servers running in the background, use the `zenml model-server list`
and `zenml model-server delete <uuid>` CLI commands.:

```shell
zenml model-deployer models delete 8cbe671b-9fce-4394-a051-68e001f92765
```

To destroy any resources deployed using the ZenML `deploy` subcommand, use the
`destroy` subcommand to delete each individual stack component, as in the
following example:

```shell
# replace with the name of the component you want to destroy
zenml artifact-store destroy s3_artifact_store
```

Then delete the remaining ZenML references:

```shell
rm -rf zenml_examples
```

# 📜 Learn more

Our docs regarding the seldon deployment integration can be found [here](https://docs.zenml.io/user-guide/component-guide/model-deployers/seldon).

If you want to learn more about deployment in ZenML in general or about how to build your own deployer steps in ZenML
check out our [docs](https://docs.zenml.io/user-guide/component-guide/model-deployers/custom).
