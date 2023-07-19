# 🚀 Custom Deployment Example - Seldon Core 🚀

Both pre- and post-processing are very essential to the model deployment 
process since the majority of the models require a specific input format 
which requires transforming the data before it is passed to the model, and 
after it is returned from the model. With ZenML, we can now ship the model 
with the pre-processing and post-processing code to run within the deployment 
environment. The custom code deployment is only supported for the Seldon Core 
model deployer integration at the moment.

Note: As this example can be considered an advanced feature of the deployment 
process, it is recommended to go through the 
[Seldon Core deployment example](https://github.com/zenml-io/zenml/tree/main/examples/seldon_deployment) 
before trying this example. That example is more focused on the deployment 
process and is easier to understand, while also providing a guide on how to 
install and setup the deployment integration.

## 🗺 Overview

This is a quite extended example that uses the [digits dataset](https://keras.io/api/datasets/mnist/) 
to train a classifier using both [TensorFlow](https://www.tensorflow.org/) and 
[PyTorch](https://pytorch.org/). Then, it deploys each of the trained models 
with the additional pre-processing and post-processing code to Seldon Core.

The example is split into two different folders and each folder contains a 
full code example of digits classification using a specific framework and 
model deployer integration. (e.g. if you want to run the TensorFlow pipeline 
within the Seldon model deployer integration, you would run the following 
command: `python run_seldon_tensoflow.py --config deploy`)

Each of these examples consists of two individual pipelines:

  * a deployment pipeline that implements a deployment workflow. It
  ingests and processes input data, trains a model and then (re)deploys the
  model with extra code to a prediction server that serves the model if it 
  meets some evaluation criteria.
  * an inference pipeline that interacts with the prediction server deployed
  by the deployment pipeline to get online predictions based on an image we 
  provide.

You can control which pipeline to run by passing the `--config deploy` or the 
`--config predict` option to the `run` launcher. The default is 
`--config deploy_and_predict` which does both.

The deployment pipeline has caching enabled to avoid re-training the model if
the training data and hyperparameter values don't change. When a new model is
trained that passes the accuracy threshold validation, the pipeline
automatically updates the currently running Seldon Core deployment 
server so that the new model is being served instead of the old one.

The inference pipeline simulates loading data (image of a digit) from a dynamic 
external source, then uses that data to perform online predictions using the 
running Seldon Core prediction server.

## 📄 Prerequisites:

For the ZenML Seldon Core deployer to work, four basic things are required:

1. access to a Kubernetes cluster. The example accepts a `--kubernetes-context`
command line argument. This Kubernetes context needs to point to the Kubernetes
cluster where Seldon Core model servers will be deployed. If the context is not 
explicitly supplied to the example, it defaults to using the locally active context.

1. Seldon Core needs to be preinstalled and running in the target 
Kubernetes cluster (read below for a brief explanation of how to do that).

1. models deployed with Seldon Core are stored in the ZenML Artifact
Store that is used to train the models (e.g. Minio, AWS S3, GCS, Azure Blob
Storage, etc.). The model deployer needs to access the artifact
store to fetch the model artifacts, which means that it may need access to
credentials for the Artifact Store, unless Seldon Core is deployed in the
same cloud as the Artifact Store and is able to access it directly without
requiring explicit credentials, through some in-cloud provider specific
implicit authentication mechanism. For this reason, you may need to configure
your Artifact Store stack component with explicit credentials. See the
section [Local and remote authentication](#local-and-remote-authentication)
for more details.

1. A container registry that is accessible from the Kubernetes cluster where
Seldon Core is installed (e.g. AWS ECR, GCR, Azure Container Registry, etc.).

## Seldon Core Setup 

For custom code deployment to work, you need to have Seldon Core deployed in a 
Kubernetes cluster. ZenML provides two ways to set up these tools:

1. A step-by-step guide on how to set up and deploy a Seldon Core deployment 
can be found in the integration example as part of the
[Seldon Core deployment guide](https://github.com/zenml-io/zenml/tree/main/examples/seldon_deployment#installing-seldon-core-eg-in-an-eks-cluster).

2. A Terraform-based recipe to provide all the required resources. More 
information can be found in the [Open Source MLOps Stack Recipes](https://github.com/zenml-io/mlops-stacks).

Once we have a ready deployment environment, we can start the example.

```shell
# install CLI
pip install "zenml[server]"

# pull example
zenml example pull custom_code_deployment
cd zenml_examples/custom_code_deployment

# initialize a local ZenML Repository
zenml init

# Start the ZenServer to enable dashboard access
zenml up
```

## Local and remote authentication

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
* the ZenML Seldon Core model deployer needs to be able to access the GCS bucket
configured for the ZenML Artifact Store, because this is where models will be
stored and loaded from.

If the ZenML orchestrator and Seldon Core are already running in the GCP cloud (e.g.
in an GKE cluster), there are ways of configuring GCP workloads to have implicit
access to other GCP resources like GCS without requiring explicit credentials.
However, if either the ZenML Orchestrator or Seldon Core is running in a
different cloud, or on-prem, or if the GCP implicit in-cloud workload
authentication is not enabled, then explicit GCP credentials are required.

Concretely, this means that the GCS Artifact Store ZenML stack component needs to
be configured with explicit GCP credentials (i.e. a GCP service account key)
that can also be used by other ZenML stack components like the ZenML
orchestrator or Seldon Core model deployer to access the bucket.

In the sections that follow, this is explained in more detail for the two
different examples of ZenML stacks featured in this document.

##### GCP Authentication with Implicit Workload Identity access

If the GKE cluster where Selodn Core is running already has
[Workload Identity](https://cloud.google.com/kubernetes-engine/docs/how-to/workload-identity)
configured to grant the GKE nodes implicit access to the GCS bucket,
you don't need to configure any explicit GCP credentials for the GCS Artifact
Store. The ZenML orchestrator and Seldon Core model deployer will
automatically default to using the environment authentication.

##### GCP Authentication with Explicit Credentials

If Workload Identity access is not configured for your GKE cluster, or you don't
know how to configure it, you will need an explicit GCP service account key that
grants access to the GCS bucket. To create a GCP service account and generate
an access key, follow the instructions in [the official GCP documentation](https://cloud.google.com/iam/docs/service-accounts-create).
Please remember to grant the created service account permissions
to read and write to your GCS bucket (i.e. use the `Storage Object Admin` role).

When you have the GCP service account key, you can configure a ZenML
secret to store them securely. You will reference the secret when you configure
the GCS Artifact Store stack component in the next sections:

```bash
zenml secret create gcp_secret \
    --token=@path/to/service/account/key.json
```

This is how you would register a ZenML GCS Artifact Store with explicit
credentials referencing the secret you just created:

```bash
zenml artifact-store register gcs_store -f gcp \
    --path='gs://your-bucket' \
    --authentication_secret=gcp_secret
```

Note that you can deploy your GCS Store using the ZenML CLI as well, using the
`zenml artifact-store deploy` command. This is how you would do it:

```shell
zenml artifact-store deploy gcs_store --flavor=gcp --project_id=my_project ...
```

For more information on this `deploy` subcommand, please refer to the 
[documentation](https://docs.zenml.io/platform-guide/set-up-your-mlops-platform/deploy-and-set-up-a-cloud-stack/deploy-a-stack-component).

## 📦 Seldon Core Custom Code Deployment

To run the Seldon Core pipelines, you need to install the integration:

```shell

# install ZenML integrations
zenml integration install tensorflow pytorch seldon

# install extra dependencies
pip install -r requirements.txt

```

### 🥞 Setting up the Seldon Core ZenML Stack

A ZenML Stack needs to be set up with all the proper components. 
Two different examples of stacks featuring GCP infrastructure components are 
described in this document, but similar stacks may be set up using different 
backends and used to run the example as long as the basic Stack prerequisites 
are met.

This stack consists of the following components:

* a GCP artifact store
* the local orchestrator
* a Seldon Core model deployer
* a GCP container registry used to store the custom Docker images used by the
Seldon Core model deployer

To have access to the GCP artifact store from your local workstation, the
`gcloud` (CLI) client needs to be properly set up locally.

In addition to the stack components, Seldon Core must be installed in a
Kubernetes cluster that is locally accessible through a Kubernetes configuration
context. The reference used in this example is a Seldon Core installation
running in a GKE cluster, but any other type of Kubernetes cluster can be used,
managed or otherwise.

To configure GKE cluster access locally, e.g:

```bash
gcloud container clusters get-credentials zenml-test-cluster --zone us-east1-b --project zenml-core
```

Set up a namespace for ZenML Seldon Core workloads:

```bash
kubectl create ns zenml-workloads
```

Extract the URL where the Seldon Core model server exposes its prediction API, e.g.:

```bash
# If you are running in GKE or AKS clusters, the host is the GKE cluster IP address.
export INGRESS_HOST=$(kubectl -n istio-system get service istio-ingressgateway -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
# If you are running in EKS clusters, the host is the EKS cluster IP hostname.
export INGRESS_HOST=$(kubectl -n istio-system get service istio-ingressgateway -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
```

Configuring the stack can be done like this:

```shell
zenml model-deployer register seldon_eks --flavor=seldon \
  --kubernetes_context=zenml-eks --kubernetes_namespace=zenml-workloads \
  --base_url=http://$INGRESS_HOST \
zenml artifact-store register gcp_artifact_store --flavor=fcp --path gs://my-bucket
zenml container-registry register gcp_registry --flavor=gcp --uri=eu.gcr.io/container-registry
zenml image-builder register local_builder --flavor=local
zenml stack register local_gcp_seldon_stack -a gcp_artifact_store -o default -d seldon_eks -c gcp_registry -i local_builder --set
```

>**Note**:
> As already covered in the [Local and remote authentication](#local-and-remote-authentication) section, you will need to configure the Artifact Store with explicit credentials if workload identity access is not configured for your GKE cluster:
> ```shell
> zenml artifact-store register gcp_artifact_store --flavor=gcp --path gs://my-bucket \
>   --authentication_secret=gcp_secret
> ```

Note that the Seldon model deployer, the GCP artifact store and the GCP
container registry can be deployed using the ZenML CLI as well, using the
`zenml <STACK_COMPONENT> deploy` command. For more information on this `deploy` subcommand, please refer to the 
[documentation](https://docs.zenml.io/platform-guide/set-up-your-mlops-platform/deploy-and-set-up-a-cloud-stack/deploy-a-stack-component).

### 🔦 Run The pipelines

The Training/Deployment pipeline consists of the following steps:
* importer - Load the MNIST handwritten digits dataset.
* train - Train a classification model using the training dataset.
* evaluate - Evaluate the model using the test dataset.
* deployment_trigger - Verify if the newly trained model exceeds the threshold 
and, if so, deploy the model.
* model_deployer - In the model deployer step, the custom predicts function 
is passed to the step configuration so that it can first be verified and then 
packaged with the model checkpoint and all the required artifacts/dependencies 
to be deployed as a custom model.

For more information about custom model deployment, please refer to the [Seldon Core integration custom deployment](https://docs.zenml.io/user-guide/component-guide/model-deployers/seldon#custom-model-deployment). 
Or the [Seldon Custom Python Model](https://docs.seldon.io/projects/seldon-core/en/latest/python/python_component.html).

The Inference pipeline consists of the following steps:
* inference_processor - Load a digits image from a URL (must be 28x28) and 
convert it to a byte array.
* prediction_service_loader - Load the prediction service into 
`SeldonDeploymentService` to perform the inference.
* predictor - Perform inference on the image using the built-in predict 
function of the prediction service.

To run the training/deployment pipeline:

```shell
# For tensorflow
python run_seldon_tensorflow.py --config="deploy"
# For pytorch
python run_seldon_pytorch.py --config="deploy"
```

Example output when run with the local orchestrator stack:

```shell
The requirements parameter has been deprecated. Please use the docker_configuration parameter instead.
The required_integrations parameter has been deprecated. Please use the docker_configuration parameter instead.
Creating run for pipeline: tensorflow_custom_code_pipeline
Cache disabled for pipeline tensorflow_custom_code_pipeline
Using stack gcp_stack_seldon to run pipeline tensorflow_custom_code_pipeline...
Step tf_data_loader has started.
Step tf_data_loader has finished in 25.235s.
Step tf_trainer has started.
1875/1875 [==============================] - 3s 2ms/step - loss: 0.4727 - accuracy: 0.8765
Step tf_trainer has finished in 23.279s.
Step tf_evaluator has started.
313/313 - 0s - loss: 0.3088 - accuracy: 0.9155 - 476ms/epoch - 2ms/step
Step tf_evaluator has finished in 9.350s.
Step deployment_trigger has started.
Step deployment_trigger has finished in 3.103s.
Step seldon_custom_model_deployer_step has started.
Building Docker image(s) for pipeline tensorflow_custom_code_pipeline.
Gathering requirements for Docker build:
        - Including user-defined requirements: Pillow
        - Including integration requirements: gcsfs, google-cloud-aiplatform>=1.11.0, google-cloud-secret-manager, kfp==1.8.9, kubernetes==18.20.0, seldon-core==1.14.0, tensorflow==2.8.0, tensorflow_io==0.24.0
Creating Docker build context from directory /home/zenml/zen/zenml/examples/custom_code_deployment.
No .dockerignore found, including all files inside build context.
Build context size for docker image: 63.86 MiB. If you believe this is unreasonably large, make sure to include a .dockerignore file at the root of your build context /home/zenml/zen/zenml/examples/custom_code_deployment/.dockerignore or specify a custom file for argument dockerignore_file when defining your pipeline.
Building Docker image gcr.io/zenml-core/zenml-kubeflow/zenml:tensorflow_custom_code_pipeline.
Building the image might take a while...
Finished building Docker image gcr.io/zenml-core/zenml-kubeflow/zenml:tensorflow_custom_code_pipeline.
Pushing Docker image gcr.io/zenml-core/zenml-kubeflow/zenml:tensorflow_custom_code_pipeline.
Finished pushing Docker image.
Creating a new Seldon deployment service: `SeldonDeploymentService[eaa6fc48-cda7-4c4e-8785-dc5b85cf0a31]` (type: model-serving, flavor: seldon)
Seldon Core deployment service started and reachable at:
    `http://35.243.201.91:80/seldon/kubeflow/zenml-eaa6fc48-cda7-4c4e-8785-dc5b85cf0a31/api/v0.1/predictions`

Step seldon_custom_model_deployer_step has finished in 4m51s.
Pipeline run `tensorflow_custom_code_pipeline-22_Aug_22-08_31_09_994315` has finished in 5m56s.
```

To run the inference pipeline:

```shell
# For tensorflow
python run_seldon_tensorflow.py --config="predict"
# For pytorch
python run_seldon_pytorch.py --config="predict"
```

Example output when run with the local orchestrator stack:

```shell
The requirements parameter has been deprecated. Please use the docker_configuration parameter instead.
The required_integrations parameter has been deprecated. Please use the docker_configuration parameter instead.
Creating run for pipeline: tensorflow_inference_pipeline
Cache disabled for pipeline tensorflow_inference_pipeline
Using stack gcp_stack_seldon to run pipeline tensorflow_inference_pipeline...
Step inference_image_loader has started.
Step inference_image_loader has finished in 7.134s.
Step seldon_prediction_service_loader has started.
Step seldon_prediction_service_loader has finished in 7.028s.
Step seldon_predictor has started.
{'predictions': ['1']}
Step seldon_predictor has finished in 4.553s.
Pipeline run tensorflow_inference_pipeline-22_Aug_22-08_38_30_970798 has finished in 22.677s.
The Seldon prediction server is running remotely as a Kubernetes service and accepts inference requests at:
    `http://35.243.201.91:80/seldon/kubeflow/zenml-eaa6fc48-cda7-4c4e-8785-dc5b85cf0a31/api/v0.1/predictions`
To stop the service, run `zenml served-models delete eaa6fc48-cda7-4c4e-8785-dc5b85cf0a31`.
```

## 🎮 ZenML Served Models CLI

The `zenml model-deployer models list` CLI command can be run to list the active
model servers:

```shell
$ zenml model-deployer models list
┏━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ STATUS │ UUID                                 │ PIPELINE_NAME                   │ PIPELINE_STEP_NAME                │ MODEL_NAME                     ┃
┠────────┼──────────────────────────────────────┼─────────────────────────────────┼───────────────────────────────────┼────────────────────────────────┨
┃   ✅   │ 0630b23b-431b-4a6a-9121-69d8036d8f24 │ pytorch_custom_code_pipeline    │ seldon_custom_model_deployer_step │ seldon-pytorch-custom-model    ┃
┠────────┼──────────────────────────────────────┼─────────────────────────────────┼───────────────────────────────────┼────────────────────────────────┨
┃   ✅   │ eaa6fc48-cda7-4c4e-8785-dc5b85cf0a31 │ tensorflow_custom_code_pipeline │ seldon_custom_model_deployer_step │ seldon-tensorflow-custom-model ┃
┗━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

To get more information about a specific model server, such as the prediction URL,
the `zenml model-deployer models describe <uuid>` CLI command can be run:

```shell
$ zenml model-deployer models describe 
                                  Properties of Served Model eaa6fc48-cda7-4c4e-8785-dc5b85cf0a31                                   
┏━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ MODEL SERVICE PROPERTY │ VALUE                                                                                                   ┃
┠────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────┨
┃ MODEL_NAME             │ seldon-tensorflow-custom-model                                                                          ┃
┠────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────┨
┃ MODEL_URI              │ gs://zenml-kubeflow-artifact-store/seldon_custom_model_deployer_step/output/1584/seldon                 ┃
┠────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────┨
┃ PIPELINE_NAME          │ tensorflow_custom_code_pipeline                                                                         ┃
┠────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────┨
┃ RUN_NAME               │ tensorflow_custom_code_pipeline-22_Aug_22-08_31_09_994315                                               ┃
┠────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────┨
┃ PIPELINE_STEP_NAME     │ seldon_custom_model_deployer_step                                                                       ┃
┠────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────┨
┃ PREDICTION_URL         │ http://35.243.201.91:80/seldon/kubeflow/zenml-eaa6fc48-cda7-4c4e-8785-dc5b85cf0a31/api/v0.1/predictions ┃
┠────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────┨
┃ SELDON_DEPLOYMENT      │ zenml-eaa6fc48-cda7-4c4e-8785-dc5b85cf0a31                                                              ┃
┠────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────┨
┃ STATUS                 │ ✅                                                                                                      ┃
┠────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────┨
┃ STATUS_MESSAGE         │ Seldon Core deployment 'zenml-eaa6fc48-cda7-4c4e-8785-dc5b85cf0a31' is available                        ┃
┠────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────┨
┃ UUID                   │ eaa6fc48-cda7-4c4e-8785-dc5b85cf0a31                                                                    ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

The prediction URL can sometimes be more difficult to make out in the detailed
output, so there is a separate CLI command available to retrieve it:

```shell
$ zenml model-deployer models get-url 
  Prediction URL of Served Model eaa6fc48-cda7-4c4e-8785-dc5b85cf0a31 is:
  http://35.243.201.91:80/seldon/kubeflow/zenml-eaa6fc48-cda7-4c4e-8785-dc5b85cf0a31/api/v0.1/predictions
  and the hostname is: No hostname specified for this service
```

Finally, a model server can be deleted with the `zenml model-deployer models delete <uuid>`
CLI command:

```shell
$ zenml model-deployer models delete eaa6fc48-cda7-4c4e-8785-dc5b85cf0a31
```

## 🧽 Clean up

To stop any prediction servers running in the background, use the 
`zenml model-server list` and `zenml model-server delete <uuid>` CLI commands.:

```shell
zenml model-deployer models delete eaa6fc48-cda7-4c4e-8785-dc5b85cf0a31
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

Our docs regarding the custom model deployment can be found 
[here](https://docs.zenml.io/user-guide/component-guide/model-deployers/model-deployers#custom-pre-processing-and-post-processing).

If you want to learn more about the deployment in ZenML in general or about 
how to build your deployer steps in ZenML check out our 
[docs](https://docs.zenml.io/user-guide/component-guide/model-deployers/custom).
