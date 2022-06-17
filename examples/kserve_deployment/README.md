# 🚀 Pytorch Models Deployment with KServe and TorchServe 

[KServe](https://kserve.github.io/website) is a Kubernetes-based Model inference platform
built for highly scalable deployment use cases, it provides a standardized inference protocol 
across ML frameworks while supporting a serverless architecture with Autoscaling including Scale to Zero on GPU.
KServe Uses a simple and pluggable production serving for production ML serving that includes 
prediction, pre/post-processing, monitoring and explainability.

Following the deployment story with ZenML that already covers a local deployment with 
[MLFlow Deployment Example](../mlflow_deployment/) and a [Seldon Core Deployment Example](../seldon_deployment/) 
as the production-grade model deployer in Kubernetes environment. The next tool that gets added to our deployment 
integrations is [KServe]() which is a Kubernetes-based Model inference platform just like Seldon Core.

KServe has built-in servers that can be used to serve models with a variety of frameworks, 
such as TensorFlow, PyTorch, TensorRT, MXNet, etc. This example shows how we can use ZenML 
to write a pipeline that trains and deploys a digits model with a SKLearn MLServer and a 
TorchServe as Runtime Servers for both frameworks using the KServe integration.

## 🗺 Overview

The example uses the digits dataset to train a classifier using both 
[scikit-learn](https://scikit-learn.org/stable/) and [PyTorch](https://pytorch.org/).
Different hyperparameter values (e.g. the number of epochs and learning rate for 
the PyTorch model, solver and penalty for the Scikit-learn logical regression) 
can be supplied as command-line arguments to the `run.py` Python script. 

The example contains three pipelines:
    * `kserve_sklearn_pipeline`: trains a classifier using Scikit-learn and deploys it to KServe with SKLearn MLServer Runtime Server.
    * `kserve_pytorch_pipeline`: trains a classifier using PyTorch and deploys it to KServe with TorchServe Runtime Server.
    * `inference_pipeline`: runs predictions on the served models.

Running the pipelines to train the classifiers and then deploying them to 
KServe requires preparing them into an exact format that is expected 
by the runtime server, storing them into remote storage or a persistent volume 
in the cluster and giving the path to KServe as the model uri with the right permissions. 
By default, ZenML's KServe integration will try to cover that for you 
by automatically loading, preparing and then saving files to the Artifact Store 
active in the ZenML stack. However, for some frameworks (e.g. Pytorch) you will still need 
to provide some additional files that Runtimes Server needs to be able to run the model. 

The KServe deployment server is provisioned remotely as a Kubernetes
resource that continues to run after the deployment pipeline run is complete.
Subsequent runs of the deployment pipeline will reuse the existing deployment
server and merely update it to serve the more recent model version.

The deployment pipeline has caching enabled to avoid re-training and
re-deploying the model if the training data and hyperparameter values don't
change. When a new model is trained that passes the accuracy threshold
validation, the pipeline automatically updates the currently running KServe
deployment server so that the new model is being served instead of the old one.

The inference pipeline load image from the local filesystem and perform 
online predictions on the running KServe inference service.


# 🖥 Local Stack

### 📄 Prerequisites 

For the ZenML KServe deployer to work, these things are required:
1. Access to a running [Kubernetes cluster](https://kubernetes.io/docs/tutorials/cluster-administration/) 
    The example accepts a `--kubernetes-context` command-line argument. This Kubernetes context needs 
    to point to the Kubernetes cluster where KServe model servers will be deployed. If the context 
    is not explicitly supplied to the example, it defaults to using the locally active context.

2. KServe must be installed and running on the Kubernetes cluster. (more information about how to
    install KServe can be found below or in the [KServe documentation](https://kserve.github.io/website/)).

3. KServe must be able to access whatever storage is used by the ZenML to save the artifact, Since the
    KServe is installed in the Kubernetes cluster, a local filesystem storage can't be used.
    We recommend using a persistent volume or a remote storage service.
    (e.g. AWS S3, GCS, Azure Blob Storage, etc.).

To run this example, you need to install and initialize ZenML:

```shell
# install CLI
pip install zenml

# install ZenML integrations
zenml integration install pytorch sklearn kserve

# pull example
zenml example pull kserve_deployment
cd zenml_examples/kserve_deployment

# initialize a local ZenML Repository
zenml init
```

### Installing KServe (e.g. in an GKE cluster)

This section is a trimmed-up version of the serverless installation guide for KServe.
[official KServe [installation instructions](https://kserve.github.io/website/0.8/admin/serverless/#recommended-version-matrix) Applied to a particular type of Kubernetes cluster, GKE in this case. It assumes that a GKE cluster is already set up and accessible.

To configure GKE cluster access locally, e.g:

```bash
gcloud container clusters get-credentials KUBERNETES_CLUSTER_NAME --zone ZONE --project PROJECT_ID
```

1. Install Istio:

We need to download [istioctl](https://istio.io/latest/docs/setup/getting-started/#download) 
Install Istio v1.12.1 (required for the latest KServe version):

```bash
curl -L https://istio.io/downloadIstio | ISTIO_VERSION=1.12.1  sh -
cd istio-1.12.1
export PATH=$PWD/bin:$PATH
# Installing Istio without sidecar injection
istioctl install -y
```

2. Installing the Knative Serving component:

```bash
# Install the required custom resources
kubectl apply -f https://github.com/knative/serving/releases/download/knative-v1.5.0/serving-crds.yaml
# Install the core components of Knative Serving
kubectl apply -f https://github.com/knative/serving/releases/download/knative-v1.5.0/serving-core.yaml
```

Install an istio networking layer:

```bash
# Install a properly configured Istio
kubectl apply -l knative.dev/crd-install=true -f https://github.com/knative/net-istio/releases/download/knative-v1.5.0/istio.yaml
kubectl apply -f https://github.com/knative/net-istio/releases/download/knative-v1.5.0/istio.yaml
# Install the Knative Istio controller
kubectl apply -f https://github.com/knative/net-istio/releases/download/knative-v1.5.0/net-istio.yaml
# Fetch the External IP address or CNAME
kubectl --namespace istio-system get service istio-ingressgateway
```

Verify the installation

```bash
kubectl get pods -n knative-serving

"""
activator-59bff9d7c8-2mgdv               1/1     Running     0          11h
autoscaler-c574c9455-x7rfn               1/1     Running     0          3d
controller-59f84c584-mm4pp               1/1     Running     0          3d
domain-mapping-75c659dbc7-hbgnl          1/1     Running     0          3d
domainmapping-webhook-6d9f5996f9-hcvcb   1/1     Running     0          3d
net-istio-controller-76bf75d78f-652fm    1/1     Running     0          11h
net-istio-webhook-9bdb8c6b9-nzf86        1/1     Running     0          11h
webhook-756688c869-79pqh                 1/1     Running     0          2d22h
"""
```
3. Install Cert Manager:

```bash
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.8.0/cert-manager.yaml
```

4. Finally, Install KServe :

```bash
# Install KServe
kubectl apply -f https://github.com/kserve/kserve/releases/download/v0.8.0/kserve.yaml
# Install KServe Built-in ClusterServingRuntimes
kubectl apply -f https://github.com/kserve/kserve/releases/download/v0.8.0/kserve-runtimes.yaml
```

### Testing the KServe deployment

To test that the installation is functional, you can use this sample KServe
deployment:

1. Create a namespace:

```bash
kubectl create namespace kserve-test
```

2. Create an InferenceService:

```bash
kubectl apply -n kserve-test -f - <<EOF
apiVersion: "serving.kserve.io/v1beta1"
kind: "InferenceService"
metadata:
  name: "sklearn-iris"
spec:
  predictor:
    model:
      modelFormat:
        name: sklearn
      storageUri: "gs://kfserving-examples/models/sklearn/1.0/model"
EOF
```

3. Check InferenceService status:

```bash
kubectl get inferenceservices sklearn-iris -n kserve-test

"""
NAME           URL                                                 READY   PREV   LATEST   PREVROLLEDOUTREVISION   LATESTREADYREVISION                    AGE
sklearn-iris   http://sklearn-iris.kserve-test.example.com         True           100                              sklearn-iris-predictor-default-47q2g   7d23h
"""
```

4. Determine the ingress IP and ports

```bash
$ kubectl get svc istio-ingressgateway -n istio-system
NAME                   TYPE           CLUSTER-IP       EXTERNAL-IP      PORT(S)   AGE
istio-ingressgateway   LoadBalancer   172.21.109.129   130.211.10.121   ...       17h
```

Extract the HOST and PORT where the model server exposes its prediction API:

```bash
export INGRESS_HOST=$(kubectl -n istio-system get service istio-ingressgateway -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
export INGRESS_PORT=$(kubectl -n istio-system get service istio-ingressgateway -o jsonpath='{.spec.ports[?(@.name=="http2")].port}')
```

5. Perform inference

Prepare your inference input request inside a file:

```bash
cat <<EOF > "./iris-input.json"
{
  "instances": [
    [6.8,  2.8,  4.8,  1.4],
    [6.0,  3.4,  4.5,  1.6]
  ]
}
EOF
```

Use curl to send a test prediction API request to the server:

```bash
SERVICE_HOSTNAME=$(kubectl get inferenceservice sklearn-iris -n kserve-test -o jsonpath='{.status.url}' | cut -d "/" -f 3)
curl -v -H "Host: ${SERVICE_HOSTNAME}" http://${INGRESS_HOST}:${INGRESS_PORT}/v1/models/sklearn-iris:predict -d @./iris-input.json
```

You should see something like this as the prediction response:

```json
{"predictions": [1, 1]}
```

### 🥞 Setting up the ZenML Stack

Before you run the example, a ZenML Stack needs to be set up with all the proper
components. Two different examples of stacks featuring GCP infrastructure
components are described in this document, but similar stacks may be set up
using different backends and used to run the example as long as the basic Stack
prerequisites are met.

#### Local orchestrator with GCS artifact store and GKE KServe installation

This stack consists of the following components:

* a GCP artifact store
* the local orchestrator
* the local metadata store
* a KServe model deployer
* a local secret manager used to store the credentials needed by KServe to
access the GCP artifact store

To have access to the GCP artifact store from your local workstation, the
gcloud client needs to be properly set up locally.

In addition to the stack components, KServe must be installed in a
Kubernetes cluster that is locally accessible through a Kubernetes configuration
context. The reference used in this example is a KServe installation
running in a GKE cluster, but any other type of Kubernetes cluster can be used,
managed or otherwise.

To configure GKE cluster access locally, e.g:

```bash
gcloud container clusters get-credentials zenml-test-cluster --zone us-east1-b --project zenml-core
```

Set up a namespace for ZenML KServe workloads:

```bash
kubectl create ns zenml-workloads
```

Extract the URL where the Seldon Core model server exposes its prediction API, e.g.:

```bash
export INGRESS_HOST=$(kubectl -n istio-system get service istio-ingressgateway -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
export INGRESS_PORT=$(kubectl -n istio-system get service istio-ingressgateway -o jsonpath='{.spec.ports[?(@.name=="http2")].port}')
export INGRESS_URL="http://${INGRESS_HOST}:${INGRESS_PORT}"
```

Configuring the stack can be done like this:

```shell
zenml integration install sklearn pytorch gcp kserve
zenml model-deployer register kserve_gke --flavor=kserve \
  --kubernetes_context=gke_zenml-core_us-east1-b_zenml-test-cluster \ 
  --kubernetes_namespace=zenml-workloads \
  --base_url=http://$INGRESS_URL \
  --secret=kserve_secret
zenml artifact-store register gcp --flavor=fcp --path gs://my-bucket
zenml secrets-manager register local --flavor=local
zenml stack register local_gcp_kserve_stack -m default -a gcp -o default -d kserve_gke -x local --set
```

As the last step in setting up the stack, we need to configure a ZenML secret
with the credentials needed by KServe to access the Artifact Store. This is
covered in the [Managing KServe Credentials section](#managing-kserve-credentials).

The next sections cover how to set GCP Artifacts store credentials for the KServe model deployer,   
Please look up the variables relevant to your use-case in the
[official KServe Storage Credentials](https://kserve.github.io/website/0.8/sdk_docs/docs/KServeClient/#parameters)
and set them accordingly for your ZenML secret.

##### GCP Authentication with kserve_gs secret schema

Before setting ZenML secrets, we need to create a service account key. 
This service account will be used to access the GCP artifact
store. for more information, see the [Create and manage service account keys](https://cloud.google.com/iam/docs/creating-managing-service-account-keys#iam-service-account-keys-create-gcloud).
Once we have the service account key, we can create a ZenML secret with the following command:

```bash
$ zenml secret register -s kserve_gs kserve_secret \
    --namespace="zenml-workloads" \
    --credentials_file="~/sa-deployment-temp.json" \

The following secret will be registered.
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━┓
┃             SECRET_KEY             │ SECRET_VALUE ┃
┠────────────────────────────────────┼──────────────┨
┃            storage_type            │ ***          ┃
┃              namespace             │ ***          ┃
┃          credentials_file          │ ***          ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━┛

$ zenml secret get kserve_secret
┏━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃    SECRET_KEY    │ SECRET_VALUE              ┃
┠──────────────────┼───────────────────────────┨
┃   storage_type   │ GCS                       ┃
┠──────────────────┼───────────────────────────┨
┃    namespace     │ kserve-test               ┃
┠──────────────────┼───────────────────────────┨
┃ credentials_file │ ~/sa-deployment-temp.json ┃
┗━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

## 🖥 Scikit-Learn Pipeline Example



## 🖥 PyTorch Pipeline Example

As Pytorch becomes more of a standard framework for writing Computer Vision
and Natural Language Processing models, especially in the research domain,
it is becoming more and more important to have a robust and easy to not only 
[build ML pipelines with Pytorch](../pytorch/) but also to deploy the models built with it.

[TorchServe](https://torchserve.github.io/website) is an open-source model serving framework for PyTorch
that makes it easy to deploy Pytorch models at a production scale with low latency and high throughput.
it provides default handlers for the most common applications such as object detection and text classification, 
so you can write as little code as possible to deploy your custom models.

