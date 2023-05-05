# 🚀 KServe Deployment Example - TensorFlow and Pytorch Examples

[KServe](https://kserve.github.io/website) is a Kubernetes-based model inference
platform built for highly scalable deployment use cases. It provides a 
standardized inference protocol across ML frameworks while supporting a 
serverless architecture with autoscaling including Scale to Zero on GPUs.
KServe uses a simple and pluggable production serving architecture for 
production ML serving that includes prediction, pre-/post-processing, 
monitoring and explainability.

Following the model deployment story within ZenML, and to make it easier to 
deploy models with other serving tools, we have created an Integration for 
KServe. But how does KServe differ from the already-integrated 
[Seldon Core](../seldon_deployment)?

* __**Supported frameworks**__: Standard ML frameworks like TensorFlow, PyTorch,
Scikit-learn, XGBoost, Keras, MXNet, etc... are first-class citizens in KServe 
and can be fairly easily used. While Seldon Core has support for the majority 
of these ML frameworks, it lacks support for Pytorch even though it could be 
still used by using the custom deployment, albeit with some extra upfront work.
* __**Custom Deployment**__: Both Seldon Core and KServe have support for 
custom deployment. However, Seldon Core offers an extra inference graph that 
includes custom [TRANSFORMER](https://docs.seldon.io/projects/seldon-core/en/latest/workflow/overview.html) 
and [ROUTER](https://docs.seldon.io/projects/seldon-core/en/latest/analytics/routers.html?highlight=routers#) 
which can be used to build more powerful inference graphs.
* __**Autoscaling**__: KServe has more advanced autoscaling features than 
Seldon Core. With the Knative autoscaling, it is possible to scale up and 
down the number of replicas of the model deployment based on the number of 
requests received.
* __**Predictions interfaces**__: Seldon Core and KServe have built-in support 
for HTTP-based protocols, However only Seldon Core has support for GRPC-based 
protocols. While it still can be configured for KServe it requires using 
manual, custom deployment.

Now that we have a clear understanding of the different features of KServe 
compared to Seldon Core, we will go through the deployment process of the model 
with KServe and focus more on how to deploy the PyTorch model.

## 🗺 Overview

The example uses the [digits dataset](https://keras.io/api/datasets/mnist/) 
to train a classifier using both [TensorFlow](https://www.tensorflow.org/)
and [PyTorch](https://pytorch.org/). Different hyperparameter values (e.g. 
the number of epochs and learning rate) can be supplied as command-line 
arguments to the `run.py` Python script. 

The example contains four pipelines:
* `tensorflow_training_deployment_pipeline`: trains a classifier using TensorFlow 
and deploys it to KServe with the TFServing Runtime Server.
* `tensorflow_inference_pipeline`: runs predictions on the Tensorflow-served 
models.
* `pytorch_training_deployment_pipeline`: trains a classifier using 
PyTorch and deploys it to KServe with TorchServe Runtime Server.
* `pytorch_inference_pipeline`: run some predictions using the deployed 
PyTorch model.

Running the pipelines to train the classifiers and then deploying them to 
KServe requires preparing them into an exact format that is expected 
by the runtime server, then storing them into remote storage or a persistent 
volume in the cluster and giving the path to KServe as the model URI with the 
right permissions to be able to retrieve the model artifacts. By default, 
ZenML's KServe integration will try to handle that for you by automatically 
loading, preparing and then saving files to the same active Artifact Store 
within the ZenML stack. However, for some frameworks (e.g. PyTorch) you will 
still need to provide some additional files that Runtime Server needs to be 
able to run the model.

Note: Pytorch models are deployed with TorchServe Runtime Server. Read more 
about how to deploy Pytorch models with TorchServe Runtime Server 
[KServe Pytorch](https://kserve.github.io/website/0.9/modelserving/v1beta1/torchserve/) 
or in [TorchServe Official documentation](https://pytorch.org/serve/).

The KServe deployment server is provisioned remotely as a Kubernetes
resource that continues to run after the deployment pipeline run is complete.
Subsequent runs of the deployment pipeline will reuse the existing deployment
server and merely update it to serve the more recent model version.

The deployment pipeline has caching enabled to avoid re-training and
re-deploying the model if the training data and hyperparameter values don't
change. When a new model is trained that passes the accuracy threshold
validation, the pipeline automatically updates the currently running KServe
deployment server so that the new model is being served instead of the old one.

The inference pipeline loads the image from the local filesystem and performs 
online predictions on the running KServe inference service.

# 🏠 Local Stack

## 📄 Infrastructure Requirements (Pre-requisites)

You don't need to set up any infrastructure to run your pipelines with KServe, locally. However, you need the following tools installed:
  * Docker must be installed on your local machine.
  * Install k3d by running `curl -s
    https://raw.githubusercontent.com/rancher/k3d/main/install.sh | bash`.

You also need to be running Linux or Windows. MacOS is currently not supported
for these local deployments.

## Create a local KServe Stack

To get a stack with KServe and potential other components, you can make use of ZenML's Stack Recipes that are a set of terraform based modules that take care of setting up a cluster with Seldon among other things.

Run the following command to deploy the local KServe stack:

```bash
zenml stack recipe deploy k3d-modular --install kserve
```

>**Note**:
> This recipe comes with MLflow, Kubeflow and Minio enabled by default. If you want any other components like Seldon or Tekton, you can specify that using the `--install/-i` flag.

This will deploy a local Kubernetes cluster with KServe installed. 
It will also generate a stack YAML file that you can import as a ZenML stack by running 

```bash
zenml stack import -f <path-to-stack-yaml>
```
Once the stack is set, you can then simply proceed to running your pipelines.

# ☁️ Cloud Stack

### 📄 Prerequisites 

To run this example, you need to install and initialize ZenML:

```shell
# install CLI
pip install "zenml[server]"

# install ZenML integrations
zenml integration install pytorch tensorflow kserve

# pull example
zenml example pull kserve_deployment
cd zenml_examples/kserve_deployment

# initialize a local ZenML Repository
zenml init

# Start the ZenServer to enable dashboard access
zenml up
```

For the ZenML KServe deployer to work, these things are required:

1. Access to a running [Kubernetes cluster](https://kubernetes.io/). The example
accepts a `--kubernetes-context` command-line argument. This Kubernetes context 
needs to point to the Kubernetes cluster where KServe model servers will be 
deployed. If the context is not explicitly supplied to the example, it defaults 
to using the locally active context.

2. KServe must be installed and running on the Kubernetes cluster (More 
information about how to install KServe can be found below or on the 
[KServe documentation](https://kserve.github.io/website/)).

3. models deployed with KServe are stored in the ZenML Artifact
Store that is used to train the models (e.g. Minio, AWS S3, GCS, Azure Blob
Storage, etc.). The KServe model deployer needs to access the artifact
store to fetch the model artifacts, which means that it may need access to
credentials for the Artifact Store, unless KServe is deployed in the
same cloud as the Artifact Store and is able to access it directly without
requiring explicit credentials, through some in-cloud provider specific
implicit authentication mechanism. For this reason, you may need to configure
your Artifact Store stack component with explicit credentials. See the
section [Local and remote authentication](#local-and-remote-authentication)
for more details.

### Installing KServe (e.g. in an GKE cluster)

This section is a trimmed-up version of the serverless installation guide for KServe,
[official KServe installation instructions](https://kserve.github.io/website/0.9/admin/serverless/#recommended-version-matrix),
applied to a particular type of Kubernetes cluster, GKE in this case. It assumes
that a GKE cluster is already set up and accessible.

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
   kubectl apply -f https://github.com/knative/serving/releases/download/knative-v1.6.0/serving-crds.yaml
   # Install the core components of Knative Serving
   kubectl apply -f https://github.com/knative/serving/releases/download/knative-v1.6.0/serving-core.yaml
   ```
   
   Install an Istio networking layer:
   
   ```bash
   # Install a properly configured Istio
   kubectl apply -l knative.dev/crd-install=true -f https://github.com/knative/net-istio/releases/download/knative-v1.6.0/istio.yaml
   kubectl apply -f https://github.com/knative/net-istio/releases/download/knative-v1.6.0/istio.yaml
   # Install the Knative Istio controller
   kubectl apply -f https://github.com/knative/net-istio/releases/download/knative-v1.6.0/net-istio.yaml
   # Fetch the External IP address or CNAME
   kubectl --namespace istio-system get service istio-ingressgateway
   ```
   
   Verify the installation:
   
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
   kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.9.1/cert-manager.yaml
   ```

4. Finally, install KServe:

   ```bash
   # Install KServe
   kubectl apply -f https://github.com/kserve/kserve/releases/download/v0.9.0/kserve.yaml
   # Install KServe Built-in ClusterServingRuntimes
   kubectl apply -f https://github.com/kserve/kserve/releases/download/v0.9.0/kserve-runtimes.yaml
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

4. Determine the ingress IP and ports:

    ```bash
    kubectl get svc istio-ingressgateway -n istio-system
    NAME                   TYPE           CLUSTER-IP       EXTERNAL-IP      PORT(S)   AGE
    istio-ingressgateway   LoadBalancer   172.21.109.129   130.211.10.121   ...       17h
    ```

    Extract the HOST and PORT where the model server exposes its prediction API:
    
    ```bash
    # For GKE clusters, the host is the GKE cluster IP address.
    export INGRESS_HOST=$(kubectl -n istio-system get service istio-ingressgateway -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
    # For EKS clusters, the host is the EKS cluster IP hostname.
    export INGRESS_HOST=$(kubectl -n istio-system get service istio-ingressgateway -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
    
    export INGRESS_PORT=$(kubectl -n istio-system get service istio-ingressgateway -o jsonpath='{.spec.ports[?(@.name=="http2")].port}')
    export INGRESS_URL="http://${INGRESS_HOST}:${INGRESS_PORT}"
    
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
    
    Use `curl` to send a test prediction API request to the server:
    
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

#### Local and remote authentication

The ZenML Stacks featured in this example are based on managed GCP services like
GCS storage, GKE Kubernetes and GCR container registry. In order to access these
services from your host, you need to have a GCP account and have the proper
credentials set up on your machine. The easiest way to do this is to install the
GCP CLI and set up CGP client credentials locally as documented in
[the official GCP documentation](https://cloud.google.com/sdk/docs/authorizing).

In addition to local access, some stack components running remotely also need
to access GCP services. For example:

* the ZenML orchestrator (e.g. Kubeflow) needs to be able to access the GCS
bucket to store and retrieve pipeline run artifacts.
* the ZenML KServe model deployer needs to be able to access the GCS bucket
configured for the ZenML Artifact Store, because this is where models will be
stored and loaded from.

If the ZenML orchestrator and KServe are already running in the GCP cloud (e.g.
in an GKE cluster), there are ways of configuring GCP workloads to have implicit
access to other GCP resources like GCS without requiring explicit credentials.
However, if either the ZenML Orchestrator or KServe is running in a
different cloud, or on-prem, or if the GCP implicit in-cloud workload
authentication is not enabled, then explicit GCP credentials are required.

Concretely, this means that the GCS Artifact Store ZenML stack component needs to
be configured with explicit GCP credentials (i.e. a GCP service account key)
that can also be used by other ZenML stack components like the ZenML
orchestrator and KServe model deployer to access the bucket.

In the sections that follow, this is explained in more detail for the two
different examples of ZenML stacks featured in this document.

##### GCP Authentication with Implicit Workload Identity access

If the GKE cluster where KServe is running already has
[Workload Identity](https://cloud.google.com/kubernetes-engine/docs/how-to/workload-identity)
configured to grant the GKE nodes implicit access to the GCS bucket,
you don't need to configure any explicit GCP credentials for the GCS Artifact
Store. The ZenML orchestrator and KServe model deployer will automatically
default to using the environment authentication.

##### GCP Authentication with Explicit Credentials

If Workload Identity access is not configured for your GKE cluster, or you don't
know how to configure it, you will need an explicit GCP service account key that
grants access to the GCS bucket. To create a GCP service account and generate
an access key, follow the instructions in [the official GCP documentation](https://cloud.google.com/iam/docs/service-accounts-create).
Please remember to grant the created service account permissions
to read and write to your GCS bucket (i.e. use the `Storage Object Admin` role).

When you have the GCP service account key, you can configure a ZenML
secret to store it securely. You will reference the secret when you configure
the GCS Artifact Store stack component in the next sections:

```bash
zenml secret create gcp_secret \
    --token=@path/to/service_account_key.json
```

This is how you would register a ZenML GCS Artifact Store with explicit
credentials referencing the secret you just created:

```bash
zenml artifact-store register gcs_store -f gcp \
    --path='gs://your-bucket' \
    --authentication_secret=gcp_secret
```


#### Local orchestrator with GCS artifact store and GKE KServe installation

This stack consists of the following components:

* a GCP artifact store
* the local orchestrator
* a KServe model deployer
* an image builder

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

Extract the URL where the KServe model server exposes its prediction API, e.g.:

```bash
# If you are running in GKE or AKS clusters, the host is the GKE cluster IP address.
export INGRESS_HOST=$(kubectl -n istio-system get service istio-ingressgateway -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
# If you are running in EKS clusters, the host is the EKS cluster IP hostname.
export INGRESS_HOST=$(kubectl -n istio-system get service istio-ingressgateway -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

export INGRESS_PORT=$(kubectl -n istio-system get service istio-ingressgateway -o jsonpath='{.spec.ports[?(@.name=="http2")].port}')
export INGRESS_URL="http://${INGRESS_HOST}:${INGRESS_PORT}"
```

Configuring the stack can be done like this:

```shell
zenml integration install tensorflow pytorch gcp kserve
zenml model-deployer register kserve_gke --flavor=kserve \
  --kubernetes_context=gke_zenml-core_us-east1-b_zenml-test-cluster \ 
  --kubernetes_namespace=zenml-workloads \
  --base_url=$INGRESS_URL \
zenml artifact-store register gcp_artifact_store --flavor=gcp --path gs://my-bucket
zenml image-builder register local_builder --flavor=local
zenml stack register local_gcp_kserve_stack -a gcp_artifact_store -o default -d kserve_gke -i local_builder --set
```

>**Note**:
> As already covered in the [Local and remote authentication](#local-and-remote-authentication) section, you will need to configure the Artifact Store with explicit credentials if workload identity access is not configured for your GKE cluster:
> ```shell
> zenml artifact-store register gcp_artifact_store --flavor=gcp --path gs://my-bucket \
>   --authentication_secret=gcp_secret
> ```

##### KServe and Remote orchestrator like Kubeflow

In order to run this example with a remote orchestrator such as Kubeflow, the 
first thing that you would require is a remote ZenML server deployed to the 
cloud. See the [deployment guide](https://docs.zenml.io/getting-started/deploying-zenml) 
for more information.

Moreover, ZenML will manage the KServe deployments inside the same `kubeflow` 
namespace where the Kubeflow pipelines are running. You also have to update the 
set of permissions granted by Kubeflow to the Kubernetes service account in the 
context of which Kubeflow pipelines are running to allow the ZenML workloads to 
create, update and delete KServe InferenceServices, Secrets and ServiceAccounts.
You can do so with the following command.

```shell
kubectl apply -n kserve-test -f - <<EOF
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: kserve-permission
  namespace: kubeflow
  labels:
    app: zenml
rules:
- apiGroups: ["serving.kserve.io",""] # "" indicates the core API group
  resources: ["inferenceservices","secrets","serviceaccounts"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: role-binding
  namespace: kubeflow
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: kserve-permission
subjects:
- kind: ServiceAccount
  name: pipeline-runner
  namespace: kubeflow
EOF
```

## 🔦 Run TensorFlow Pipeline

[TFServing](https://www.tensorflow.org/tfx/guide/serving) TensorFlow Serving 
is a flexible, high-performance serving system for machine learning models, 
designed for production environments. TensorFlow Serving makes it easy to 
deploy new algorithms and experiments while keeping the same server architecture
and APIs. TensorFlow Serving provides out-of-the-box integration with TensorFlow
models but can be easily extended to serve other types of models and data.

The TensorFlow pipeline consists of the following steps:
* importer - Load the MNIST handwritten digits dataset from the TensorFlow 
library
* train - Train a Support Vector Classifier model using the training dataset.
* evaluate - Evaluate the model using the test dataset.
* deployment_trigger - Verify if the newly trained model exceeds the threshold 
and if so, deploy the model.
* model_deployer - Deploy the TensorFlow model to the KServe model server using 
the TFServing runtime server. the model_deployer is a ZenML built-in step that 
takes care of the preparing of the model to the 
[right format](https://www.tensorflow.org/guide/saved_model) for the runtime 
servers. In this case, the ZenML will be saving a file with the name 
`tf.saved_model` in the artifact store which is the format that the 
runtime servers expect.

Note: The ZenML built-in model deployer step has a set of parameters that can 
be used to define the type of kserve used server and used Kubernetes resources.
Some parameters within the `KServeDeploymentConfig` you can configure:

* `model_name`: the name of the model in the KServe cluster and in ZenML.
* `replicas`: the number of replicas with which to deploy the model
* `predictor`: the type of predictor to use for the model. The
predictor type can be one of the following: `tensorflow`, `pytorch`, `sklearn`, 
`xgboost`, `custom`.
* `resources`: This can be configured by passing a dictionary with the
`requests` and `limits` keys. The values for these keys can be a dictionary
with the `cpu` and `memory` keys. The values for these keys can be a string
with the amount of CPU and memory to be allocated to the model.

### 🏃️ Run the code
To run the training/deployment TensorFlow pipeline:

```shell
python run_tensorflow.py --config="deploy"
```

Example output when run with the local orchestrator stack:

```shell
Creating run for pipeline: tensorflow_training_deployment_pipeline
Cache enabled for pipeline tensorflow_training_deployment_pipeline
Using stack gcp_stack_kserve to run pipeline tensorflow_training_deployment_pipeline...
Step importer_mnist has started.
Using cached version of importer_mnist.
Step importer_mnist has finished in 0.070s.
Step normalizer has started.
Using cached version of normalizer.
Step normalizer has finished in 0.068s.
Step tf_trainer has started.
Using cached version of tf_trainer.
Step tf_trainer has finished in 0.055s.
Step tf_evaluator has started.
Using cached version of tf_evaluator.
Step tf_evaluator has finished in 0.064s.
Step deployment_trigger has started.
Using cached version of deployment_trigger.
Step deployment_trigger has finished in 0.044s.
Step kserve_model_deployer_step has started.
INFO:kserve.api.creds_utils:Created Secret: `kserve-secret-7k6p2` in namespace kubeflow
INFO:kserve.api.creds_utils:Patched Service account: kserve-service-credentials in namespace kubeflow
Creating a new KServe deployment service: `KServeDeploymentService[a9e967a1-9b26-4d5c-855c-e5abba0b020b]` (type: model-serving, flavor: kserve)
KServe deployment service started and reachable at:
    `http://35.243.201.91:80/v1/models/mnist-tensorflow:predict`
    With the hostname: `mnist-tensorflow.kubeflow.example.com.`
Step `kserve_model_deployer_step` has finished in 29.502s.
Pipeline run `tensorflow_training_deployment_pipeline-24_Jul_22-23_57_50_176513` has finished in 31.799s.
``` 

Example of the Tensorflow training/deployment pipeline when run with the 
remote Kubeflow stack:

![Tensorflow Training/Deployment Pipeline](assets/tensorflow_train_deploy_remote.png)

To run the TensorFlow Inference pipeline:

```shell
python run_tensorflow.py --config="predict"
```

```shell
Creating run for pipeline: tensorflow_inference_pipeline
Cache enabled for pipeline tensorflow_inference_pipeline
Using stack gcp_stack_kserve to run pipeline tensorflow_inference_pipeline...
Step prediction_service_loader has started.
Step prediction_service_loader has finished in 5.918s.
Step tf_predict_preprocessor has started.
Step tf_predict_preprocessor has finished in 6.287s.
Step tf_predictor has started.
Prediction:  [0]
Step tf_predictor has finished in 9.659s.
Pipeline run `tensorflow_inference_pipeline-24_Jul_22-23_58_24_922079` has finished in 23.932s.
The KServe prediction server is running remotely as a Kubernetes service and accepts inference requests at:
    `http://35.243.201.91:80/v1/models/mnist-tensorflow:predict`
    With the hostname: `mnist-tensorflow.kubeflow.example.com.`
To stop the service, run `zenml model-deployer models delete a9e967a1-9b26-4d5c-855c-e5abba0b020b`.
```

Example of the Tensorflow inference pipeline when run with the remote Kubeflow 
stack:

![Tensorflow Inference Pipeline](assets/tensorflow_inference_remote.png)


To stop the service, re-run the same command and supply the `--stop-service` 
argument.

## 🖥 Run PyTorch Pipeline

As PyTorch becomes more of a standard framework for writing Computer Vision
and Natural Language Processing models, especially in the research domain,
it is becoming more and more important to have a robust and easy to not only 
[build ML pipelines with Pytorch](../pytorch/) but also to deploy the models 
built with it.

[TorchServe](https://github.com/pytorch/serve) is an open-source model serving 
framework for PyTorch that makes it easy to deploy Pytorch models at a 
production scale with low latency and high throughput, it provides default 
handlers for the most common applications such as object detection and text 
classification, so you can write as little code as possible to deploy your 
custom models.

The PyTorch Training/Deployment pipeline consists of the following steps:

* importer - Load the MNIST handwritten digits dataset from the TorchVision 
library
* train - Train a neural network using the training set. The network is defined 
in the `mnist.py` file in the PyTorch folder.
* evaluate - Evaluate the model using the test set.
* deployment_trigger - Verify if the newly trained model exceeds the threshold 
and if so, deploy the model.
* model_deployer - Deploy the trained model to the KServe model server using 
the TorchServe runtime.

Just like the TFServing runtime, the `model_deployer` is a ZenML built-in step 
that takes care of the preparing of the model to the right format for the 
runtime servers. But in this case, the user must provide some extra files to 
the config parameters of the `model_deployer` step.

Some of the parameters that TorchServe expects are:

- `model_class_file`: Python script containing model architecture class.
- `handler`: TorchServe's handler file to handle custom TorchServe inference 
logic.
- `torch_config`: TorchServe configuration file. By default, ZenML generates 
a config file for you. You can also provide your config file.

For more information about the TorchServe runtime, please refer to the 
[TorchServe InferenceService](https://kserve.github.io/website/0.8/modelserving/v1beta1/torchserve/#create-the-torchserve-inferenceservice) 
or the [TorchServe Github Repository](https://github.com/pytorch/serve).

The PyTorch Inference pipeline consists of the following steps:

* pytorch_inference_processor - Load a digits image from URL (must be 28x28) 
and convert it to a byte array.
* prediction_service_loader - Load the prediction service into 
KServeDeploymentService to perform the inference.
* predictor - Perform inference on the image using the built-in predict 
function of the prediction service.

### 🏃️ Run the code

To run the PyTorch training/deployment pipeline:

```shell
python run_pytorch.py --config="deploy"
```

Example output when running the pipeline with the local orchestrator stack:

```shell
Creating run for pipeline: pytorch_training_deployment_pipeline
Cache enabled for pipeline pytorch_training_deployment_pipeline
Using stack local_gcp_kserve_stack to run pipeline pytorch_training_deployment_pipeline...
Step pytorch_data_loader has started.
Using cached version of pytorch_data_loader.
Step pytorch_data_loader has finished in 0.040s.
Step pytorch_trainer has started.
Using cached version of pytorch_trainer.
Step pytorch_trainer has finished in 0.034s.
Step pytorch_evaluator has started.
Using cached version of pytorch_evaluator.
Step pytorch_evaluator has finished in 0.041s.
Step deployment_trigger has started.
Using cached version of deployment_trigger.
Step deployment_trigger has finished in 0.032s.
Step kserve_model_deployer_step has started.
INFO:root:Successfully exported model mnist-pytorch to file `/tmp/zenml-pytorch-temp-j_bx9x1f`
INFO:kserve.api.creds_utils:Created Secret: `kserve-secret-gqktl` in namespace zenml-workloads
INFO:kserve.api.creds_utils:Patched Service account: kserve-service-credentials in namespace zenml-workloads
Creating a new KServe deployment service: `KServeDeploymentService[e7595ac9-7fcf-42c2-82ac-a9e40ee95090]` (type: model-serving, flavor: kserve)
KServe deployment service started and reachable at:
    `http://104.196.187.43:80/v1/models/mnist-pytorch:predict`
    With the hostname: `mnist-pytorch.zenml-workloads.example.com.`
Step kserve_model_deployer_step has finished in 31.207s.
Pipeline run pytorch_training_deployment_pipeline-04_Aug_22-00_32_11_318689 has finished in 31.667s.
The KServe prediction server is running remotely as a Kubernetes service and accepts inference requests at:
    `http://104.196.187.43:80/v1/models/mnist-pytorch:predict`
    With the hostname: `mnist-pytorch.zenml-workloads.example.com.`
To stop the service, run `zenml model-deployer models delete e7595ac9-7fcf-42c2-82ac-a9e40ee95090`.
```

Example of the PyTorch training/deployment pipeline when run with the remote 
Kubeflow stack:

![PyTorch Training/Deployment Pipeline](assets/pytorch_train_deploy_remote.png)

To run the PyTorch inference pipeline:

```shell
python run_pytorch.py --config="predict"
```

Example output when running the pipeline with the local orchestrator stack:

```shell
Creating run for pipeline: pytorch_inference_pipeline
Cache enabled for pipeline pytorch_inference_pipeline
Using stack local_gcp_kserve_stack to run pipeline pytorch_inference_pipeline...
Step prediction_service_loader has started.
Step prediction_service_loader has finished in 2.910s.
Step pytorch_inference_processor has started.
Step pytorch_inference_processor has finished in 1.664s.
Step pytorch_predictor has started.
Prediction: 
[1]
Step pytorch_predictor has finished in 4.075s.
Pipeline run `pytorch_inference_pipeline-04_Aug_22-00_35_16_493511` has finished in 8.883s.
The KServe prediction server is running remotely as a Kubernetes service and accepts inference requests at:
    `http://104.196.187.43:80/v1/models/mnist-pytorch:predict`
    With the hostname: `mnist-pytorch.zenml-workloads.example.com.`
To stop the service, run `zenml model-deployer models delete e7595ac9-7fcf-42c2-82ac-a9e40ee95090`.
```

Example of the PyTorch inference pipeline when run with the remote Kubeflow 
stack:

![PyTorch Inference Pipeline](assets/pytorch_inference_remote.png)


## 🎮 ZenML Served Models CLI

The `zenml model-deployer models list` CLI command can be run to list the 
active model servers:

```shell
$ zenml model-deployer models list
┏━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━┓
┃ STATUS │ UUID                                 │ PIPELINE_NAME                           │ PIPELINE_STEP_NAME         │ MODEL_NAME       ┃
┠────────┼──────────────────────────────────────┼─────────────────────────────────────────┼────────────────────────────┼──────────────────┨
┃   ✅   │ e7595ac9-7fcf-42c2-82ac-a9e40ee95090 │ pytorch_training_deployment_pipeline    │ kserve_model_deployer_step │ mnist-pytorch    ┃
┠────────┼──────────────────────────────────────┼─────────────────────────────────────────┼────────────────────────────┼──────────────────┨
┃   ✅   │ 62aac6aa-88fd-4eb7-a753-b46f1658775c │ tensorflow_training_deployment_pipeline │ kserve_model_deployer_step │ mnist-tensorflow ┃
┗━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━┛
```

To get more information about a specific model server, such as the prediction 
URL, the `zenml model-deployer models describe <uuid>` CLI command can be run:

```shell
$ zenml model-deployer models describe a9e967a1-9b26-4d5c-855c-e5abba0b020b
  Properties of Served Model 62aac6aa-88fd-4eb7-a753-b46f1658775c                                      
┏━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ MODEL SERVICE PROPERTY   │ VALUE                                                                                                       ┃
┠──────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────┨
┃ KSERVE_INFERENCE_SERVICE │ mnist-tensorflow                                                                                            ┃
┠──────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────┨
┃ MODEL_NAME               │ mnist-tensorflow                                                                                            ┃
┠──────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────┨
┃ MODEL_URI                │ gs://zenml-kubeflow-artifact-store/kserve_model_deployer_step/output/706/kserve/tensorflow/mnist-tensorflow ┃
┠──────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────┨
┃ PIPELINE_NAME            │ tensorflow_training_deployment_pipeline                                                                     ┃
┠──────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────┨
┃ RUN_NAME                 │ tensorflow_training_deployment_pipeline-25_Jul_22-00_17_10_197418                                           ┃
┠──────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────┨
┃ PIPELINE_STEP_NAME       │ kserve_model_deployer_step                                                                                  ┃
┠──────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────┨
┃ PREDICTION_HOSTNAME      │ mnist-tensorflow.kubeflow.example.com                                                                       ┃
┠──────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────┨
┃ PREDICTION_URL           │ http://35.243.201.91:80/v1/models/mnist-tensorflow:predict                                                  ┃
┠──────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────┨
┃ STATUS                   │ ✅                                                                                                          ┃
┠──────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────┨
┃ STATUS_MESSAGE           │ Inference service 'mnist-tensorflow' is available                                                           ┃
┠──────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────┨
┃ UUID                     │ 62aac6aa-88fd-4eb7-a753-b46f1658775c                                                                        ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

The prediction URL can sometimes be more difficult to make out in the detailed
output, so there is a separate CLI command available to retrieve it:


```shell
$ zenml model-deployer models get-url a9e967a1-9b26-4d5c-855c-e5abba0b020b
  Prediction URL of Served Model 62aac6aa-88fd-4eb7-a753-b46f1658775c is:
  http://35.243.201.91:80/v1/models/mnist-tensorflow:predict
  and the hostname is: mnist-tensorflow.kubeflow.example.com
```

Finally, a model server can be deleted with the `zenml model-deployer models delete <uuid>`
CLI command:

```shell
$ zenml model-deployer models delete 62aac6aa-88fd-4eb7-a753-b46f1658775c
```

## 🧽 Clean up

To stop any prediction servers running in the background, use the `zenml model-server list`
and `zenml model-server delete <uuid>` CLI commands.:

```shell
zenml model-deployer models delete 62aac6aa-88fd-4eb7-a753-b46f1658775c
```

Then delete the remaining ZenML references.

```shell
rm -rf zenml_examples
```

# 📜 Learn more

Our docs regarding the KServe deployment integration can be found 
[here](https://docs.zenml.io/component-gallery/model-deployers/kserve).

If you want to learn more about deployment in ZenML in general or about how 
to build your own deployer steps in ZenML check out our 
[docs](https://docs.zenml.io/component-gallery/model-deployers/custom).
