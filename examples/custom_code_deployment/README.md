# 🚀 Custom Deployment Example - Seldon Core and KServe 🚀

Both pre and post-processing are very essential to the model deployment process since the majority of the models require a specific input format which requires transforming the data before it is passed to the model and after it is returned from the model. with ZenML 0.13 we can now ship the model with the pre-processing and post-processing code to run within the deployment environment.
The custom code deployment is only supported for the KServe and Seldon Core model deployer integrations at the moment.

Note: As this example can be considered an advanced feature of the deployment process, it is recommended to go through the [KServe deployment example](https://github.com/zenml-io/zenml/tree/main/examples/kserve_deployment) and/or the [Seldon Core deployment example](https://github.com/zenml-io/zenml/tree/main/examples/seldon_deployment) before trying this example. Those examples are more focused on the deployment process and are easier to understand, while also providing a guide on how to install and setup each of the deployment integrations.
## 🗺 Overview

This is a quite extended example that uses the [digits dataset](https://keras.io/api/datasets/mnist/) 
to train a classifier using both [TensorFlow](https://www.tensorflow.org/)
and [PyTorch](https://pytorch.org/). Then it deploys each of the trained models with the additional pre-processing and post-processing code to both KServe and Seldon Core.

The example is split into four different folders and each folder contains a full code example of digits classification using a specific framework and model deployer integration. (e.g. if you want to run the TensorFlow pipeline within the KServe model deployer integration, you would run the following command: `python run_kserve_tensoflow.py --config deploy`)

Each of these examples consists of two individual pipelines:

  * a deployment pipeline that implements a deployment workflow. It
  ingests and processes input data, trains a model and then (re)deploys the
  model with extra code to a prediction server that serves the model if it 
  meets some evaluation criteria
  * an inference pipeline that interacts with the prediction server deployed
  by the deployment pipeline to get online predictions based on an image we 
  provide.

You can control which pipeline to run by passing the `--config deploy` or the 
`--config predict` option to the `run` launcher. The default is 
`--config deploy_and_predict` which does both.

The deployment pipeline has caching enabled to avoid re-training the model if
the training data and hyperparameter values don't change. When a new model is
trained that passes the accuracy threshold validation, the pipeline
automatically updates the currently running Seldon Core or KServe deployment 
server so that the new model is being served instead of the old one.

The inference pipeline simulates loading data (image of a digit) from a dynamic 
external source, then uses that data to perform online predictions using the 
running Seldon Core or KServe prediction server.

## 📄 Prerequisites:

For the ZenML Seldon Core / KServe deployer to work, four basic things are 
required:

1. access to a Kubernetes cluster. The example accepts a `--kubernetes-context`
command line argument. This Kubernetes context needs to point to the Kubernetes
cluster where Seldon Core or KServe model servers will be deployed. If the 
context is not explicitly supplied to the example, it defaults to using the 
locally active context.

2. Seldon Core or KServe needs to be preinstalled and running in the target 
Kubernetes cluster (read below for a brief explanation of how to do that).

3. models deployed with Seldon Core need to be stored in some form of
persistent shared storage that is accessible from the Kubernetes cluster where
Seldon Core or KServe is installed (e.g. AWS S3, GCS, Azure Blob Storage, etc.).

4. A container registry that is accessible from the Kubernetes cluster where
Seldon Core or KServe is installed (e.g. AWS ECR, GCR, Azure Container Registry,
etc.).

## Seldon Core / KServe Setup 

For custom code deployment to work, you need to have either a Seldon Core or KServe
deployed in a Kubernetes cluster. ZenML provides two ways to setup these tools:

1. A step-by-step guide on how to setup and deploy a Seldon Core deployment can be found
in the integration example.
    * [KServe deployment guide](https://github.com/zenml-io/zenml/tree/main/examples/kserve_deployment#installing-kserve-eg-in-an-gke-cluster)
    * [Seldon Core deployment guide](https://github.com/zenml-io/zenml/tree/main/examples/seldon_deployment#installing-seldon-core-eg-in-an-eks-cluster).

2. A Terraform-based recipe to provide all the required resources. More information can be found in the 
[Open Source MLOps Stack Recipes](https://github.com/zenml-io/mlops-stacks).


Once we have a ready deployment environment, we can start the example.

```shell
# install CLI
pip install zenml

# pull example
zenml example pull custom_code_deployment
cd zenml_examples/custom_code_deployment

# initialize a local ZenML Repository
zenml init
```

We will split this into 2 main sections, one for KServe and one for Seldon Core.

## 📦 KServe Custom Code Deployment

To run the KServe pipelines, you need to install the integration:

```shell

# install ZenML integrations
zenml integration install tensorflow pytorch kserve

# install extra dependencies
pip install -r requirements.txt

```

### 🥞 Setting up the KServe ZenML Stack

A ZenML Stack needs to be set up with all the proper components. 
Two different examples of stacks featuring GCP infrastructure components are 
described in this document, but similar stacks may be set up using different 
backends and used to run the example as long as the basic Stack prerequisites 
are met.

This stack consists of the following components:

* a GCP artifact store
* the local orchestrator
* the local metadata store
* a KServe model deployer
* a local secret manager used to store the credentials needed by KServe to
access the GCP artifact store
* a GCP container registry used to store the custom Docker images used by the
KServe model deployer

To have access to the GCP artifact store from your local workstation, the
`gcloud` (CLI) client needs to be properly set up locally.

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
zenml model-deployer register kserve_gke --flavor=kserve \
  --kubernetes_context=gke_zenml-core_us-east1-b_zenml-test-cluster \ 
  --kubernetes_namespace=zenml-workloads \
  --base_url=$INGRESS_URL \
  --secret=kserve_secret
zenml artifact-store register gcp_artifact_store --flavor=fcp --path gs://my-bucket
zenml secrets-manager register local --flavor=local
zenml container-registry register gcp_registry --flavor=gcp --uri=eu.gcr.io/container-registry
zenml stack register local_gcp_kserve_stack -m default -a gcp_artifact_store -o default -d kserve_gke -c gcp_registry -x local --set
```

The next sections cover how to setup the GCP Artifact Store credentials for the KServe model deployer. 
Please look up the variables relevant to your use case in the
[official KServe Storage Credentials](https://kserve.github.io/website/0.8/sdk_docs/docs/KServeClient/#parameters)
and set them accordingly for your ZenML secrets schemas already built for each storage_type.
You can find the relevant variables in the [Kserve integration secret schemas docs](https://apidocs.zenml.io/latest/api_docs/integrations/#zenml.integrations.kserve.secret_schemas.secret_schemas).

#### GCP Authentication with kserve_gs secret schema

> **Note**
> If you're coming to this section after deploying the [`gke-kubeflow-kserve` recipe](https://github.com/zenml-io/mlops-stacks/tree/main/gcp-kubeflow-kserve), you already have a service account created for you. The service account key is available as a file named `kserve_sa_key.json` in the root directory of your recipe. You can jump straight to the `zenml secrets-manager secret register` command below to register your secret!

Before setting ZenML secrets, we need to create a service account key. 
This service account will be used to access the GCP Artifact
Store. for more information, see the [Create and manage service account keys](https://cloud.google.com/iam/docs/creating-managing-service-account-keys#iam-service-account-keys-create-gcloud).
Once we have the service account key, we can create a ZenML secret with the following command:

```bash
zenml secrets-manager secret register -s kserve_gs kserve_secret \
    --credentials="@~/sa-deployment-temp.json" \

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━┓
┃             SECRET_KEY             │ SECRET_VALUE ┃
┠────────────────────────────────────┼──────────────┨
┃            storage_type            │ ***          ┃
┃             credentials            │ ***          ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━┛
``` 

```bash
zenml secrets-manager secret get kserve_secret
┏━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃    SECRET_KEY    │ SECRET_VALUE              ┃
┠──────────────────┼───────────────────────────┨
┃   storage_type   │ GCS                       ┃
┠──────────────────┼───────────────────────────┨
┃   credentials    │ ~/sa-deployment-temp.json ┃
┗━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

### 🔦 Run The pipelines

The Training/Deployment pipeline consists of the following steps:
* importer - Load the MNIST handwritten digits dataset.
* train - Train a classification model using the training dataset.
* evaluate - Evaluate the model using the test dataset.
* deployment_trigger - Verify if the newly trained model exceeds the threshold and, if so, deploy the model.
* model_deployer - In the model deployer step, the custom predicts function is passed to the step configuration 
  so that it can first be verified and then packaged with the model checkpoint and all the required artifacts/dependencies
  to be deployed as a custom model.

For more information about custom model deployment, please refer to the [KServe integration custom deployment](https://docs.zenml.io/mlops-stacks/model-deployers/kserve#custom-model-deployment). 
Or the [KServe Custom Predictor](https://kserve.github.io/website/0.9/modelserving/v1beta1/custom/custom_model/).

The Inference pipeline consists of the following steps:
* inference_processor - Load a digits image from a URL (must be 28x28) and convert it to a byte array.
* prediction_service_loader - Load the prediction service into `KServeDeploymentService` to perform the inference.
* predictor - Perform inference on the image using the built-in predict function of the prediction service.

To run the training/deployment pipeline:

```shell
# For tensorflow
python run_kserve_tensorflow.py --config="deploy"
# For pytorch
python run_kserve_pytorch.py --config="deploy"
```

Example output when run with the local orchestrator stack:

```shell
The requirements parameter has been deprecated. Please use the docker_configuration parameter instead.
The required_integrations parameter has been deprecated. Please use the docker_configuration parameter instead.
Creating run for pipeline: pytorch_custom_code_pipeline
Cache disabled for pipeline pytorch_custom_code_pipeline
Using stack gcp_stack_kserve to run pipeline pytorch_custom_code_pipeline...
Step pytorch_data_loader has started.
Step pytorch_data_loader has finished in 14.157s.
Step pytorch_trainer has started.
Train Epoch: 1  Loss: 0.710622
Train Epoch: 2  Loss: 0.147932
Train Epoch: 3  Loss: 0.877334
Step pytorch_trainer has finished in 3m59s.
Step pytorch_evaluator has started.
Test set: Average loss: 0.2976, Accuracy: 9179/10000 (92%)
Step pytorch_evaluator has finished in 16.551s.
Step deployment_trigger has started.
Step deployment_trigger has finished in 7.751s.
Step kserve_custom_model_deployer_step has started.
Building Docker image(s) for pipeline pytorch_custom_code_pipeline.
Gathering requirements for Docker build:
        - Including user-defined requirements: torchvision
        - Including integration requirements: gcsfs, google-cloud-aiplatform>=1.11.0, google-cloud-secret-manager, kfp==1.8.9, kserve==0.9.0, torch, torch-model-archiver
Creating Docker build context from directory /home/zenml/zen/zenml/examples/custom_code_deployment.
No .dockerignore found, including all files inside build context.
Build context size for docker image: 63.86 MiB. If you believe this is unreasonably large, make sure to include a .dockerignore file at the root of your build context /home/zenml/zen/zenml/examples/custom_code_deployment/.dockerignore or specify a custom file for argument dockerignore_file when defining your pipeline.
Building Docker image gcr.io/zenml-core/zenml-kubeflow/zenml:pytorch_custom_code_pipeline.
Building the image might take a while...
Finished building Docker image gcr.io/zenml-core/zenml-kubeflow/zenml:pytorch_custom_code_pipeline.
Pushing Docker image gcr.io/zenml-core/zenml-kubeflow/zenml:pytorch_custom_code_pipeline.
Finished pushing Docker image.
INFO:kserve.api.creds_utils:Created Secret: `kserve-secret-h6trl` in namespace kubeflow
INFO:kserve.api.creds_utils:Patched Service account: `kserve-service-credentials` in namespace kubeflow
Creating a new KServe deployment service: `KServeDeploymentService[ed25e3f4-23f0-4e1d-b545-8531684ffbd5]` (type: model-serving, flavor: kserve)
KServe deployment service started and reachable at:
    `http://35.243.201.91:80/v1/models/kserve-pytorch-custom-model:predict`
    With the hostname: `kserve-pytorch-custom-model.kubeflow.example.com.`
Step kserve_custom_model_deployer_step has finished in 59.894s.
Pipeline run `pytorch_custom_code_pipeline-22_Aug_22-07_43_02_628892` has finished in 5m42s.
```

To run the inference pipeline:

```shell
# For tensorflow
python run_kserve_tensorflow.py --config="predict"
# For pytorch
python run_kserve_pytorch.py --config="predict"
```

Example output when run with the local orchestrator stack:

```shell
The requirements parameter has been deprecated. Please use the docker_configuration parameter instead.
The required_integrations parameter has been deprecated. Please use the docker_configuration parameter instead.
Creating run for pipeline: pytorch_inference_pipeline
Cache disabled for pipeline pytorch_inference_pipeline
Using stack gcp_stack_kserve to run pipeline pytorch_inference_pipeline...
Step inference_image_loader has started.
Step inference_image_loader has finished in 7.383s.
Step kserve_prediction_service_loader has started.
Step kserve_prediction_service_loader has finished in 6.941s.
Step kserve_predictor has started.
{'predictions': ['1']}
Step kserve_predictor has finished in 6.970s.
Pipeline run `pytorch_inference_pipeline-22_Aug_22-07_51_15_317343` has finished in 25.420s.
The KServe prediction server is running remotely as a Kubernetes service and accepts inference requests at:
    `http://35.243.201.91:80/v1/models/kserve-pytorch-custom-model:predict`
    With the hostname: `kserve-pytorch-custom-model.kubeflow.example.com.`
To stop the service, run `zenml served-models delete ed25e3f4-23f0-4e1d-b545-8531684ffbd5`.
```

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
* the local metadata store
* a Seldon Core model deployer
* a local secrets manager used to store the credentials needed by Seldon Core to
access the GCP artifact store
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
  --secret=s3-store
zenml artifact-store register gcp_artifact_store --flavor=fcp --path gs://my-bucket
zenml secrets-manager register local --flavor=local
zenml container-registry register gcp_registry --flavor=gcp --uri=eu.gcr.io/container-registry
zenml stack register local_gcp_seldon_stack -m default -a gcp_artifact_store -o default -d seldon_eks -c gcp_registry -x local --set
```

The next sections cover how to set GCP Artifact Store credentials for the Seldon Core model deployer.  
Please look up the variables relevant to your use case in the
[official Seldon Core Storage Credentials](https://kserve.github.io/website/0.8/sdk_docs/docs/KServeClient/#parameters)
and set them accordingly for your ZenML secrets schemas already built for each storage_type.
You can find the relevant variables in the [Seldon Integration secret schema](https://apidocs.zenml.io/latest/api_docs/integrations/#zenml.integrations.seldon.secret_schemas.secret_schemas).

#### GCP Authentication with seldon_s3 secret schema

Before setting ZenML secrets, we need to create a service account key. 
This service account will be used to access the GCP Artifact
Store. for more information, see the [Create and manage service account keys](https://cloud.google.com/iam/docs/creating-managing-service-account-keys#iam-service-account-keys-create-gcloud).
Once we have the service account key, we can create a ZenML secret with the following command:

```bash
$ zenml secrets-manager secret register -s seldon_s3 s3-store \
    --rclone_config_s3_env_auth=False \
    --rclone_config_s3_access_key_id='ASAK2NSJVO4HDQC7Z25F' \ --rclone_config_s3_secret_access_key='AhkFSfhjj23fSDFfjklsdfj34hkls32SDfscsaf+' \
    --rclone_config_s3_session_token=@./aws_session_token.txt \
    --rclone_config_s3_region=us-east-1
Expanding argument value rclone_config_s3_session_token to contents of file ./aws_session_token.txt.
The following secret will be registered.
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━┓
┃             SECRET_KEY             │ SECRET_VALUE ┃
┠────────────────────────────────────┼──────────────┨
┃       rclone_config_s3_type        │ ***          ┃
┃     rclone_config_s3_provider      │ ***          ┃
┃     rclone_config_s3_env_auth      │ ***          ┃
┃   rclone_config_s3_access_key_id   │ ***          ┃
┃ rclone_config_s3_secret_access_key │ ***          ┃
┃   rclone_config_s3_session_token   │ ***          ┃
┃      rclone_config_s3_region       │ ***          ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━┛
INFO:botocore.credentials:Found credentials in shared credentials file: ~/.aws/credentials

$ zenml secrets-manager secret get s3-store
INFO:botocore.credentials:Found credentials in shared credentials file: ~/.aws/credentials
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃             SECRET_KEY             │ SECRET_VALUE                           ┃
┠────────────────────────────────────┼────────────────────────────────────────┨
┃       rclone_config_s3_type        │ s3                                     ┃
┃     rclone_config_s3_provider      │ aws                                    ┃
┃     rclone_config_s3_env_auth      │ False                                  ┃
┃   rclone_config_s3_access_key_id   │ ASAK2NSJVO4HDQC7Z25F                   ┃
┃ rclone_config_s3_secret_access_key │ AhkFSfhjj23fSDFfjklsdfj34hkls32SDfscs… ┃
┃   rclone_config_s3_session_token   │ FwoGZXIvYXdzEG4aDHogqi7YRrJyVJUVfSKpA… ┃
┃                                    │                                        ┃
┃      rclone_config_s3_region       │ us-east-1                              ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

### 🔦 Run The pipelines

The Training/Deployment pipeline consists of the following steps:
* importer - Load the MNIST handwritten digits dataset.
* train - Train a classification model using the training dataset.
* evaluate - Evaluate the model using the test dataset.
* deployment_trigger - Verify if the newly trained model exceeds the threshold and, if so, deploy the model.
* model_deployer - In the model deployer step, the custom predicts function is passed to the step configuration 
  so that it can first be verified and then packaged with the model checkpoint and all the required artifacts/dependencies
  to be deployed as a custom model.

For more information about custom model deployment, please refer to the [Seldon Core integration custom deployment](https://docs.zenml.io/mlops-stacks/model-deployers/seldon#custom-model-deployment). 
Or the [Seldon Custom Python Model](https://docs.seldon.io/projects/seldon-core/en/latest/python/python_component.html).

The Inference pipeline consists of the following steps:
* inference_processor - Load a digits image from a URL (must be 28x28) and convert it to a byte array.
* prediction_service_loader - Load the prediction service into `SeldonDeploymentService` to perform the inference.
* predictor - Perform inference on the image using the built-in predict function of the prediction service.

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

The `zenml model-deployer models list` CLI command can be run to list the active model servers:

```shell
$ zenml model-deployer models list
# For the Seldon Core Model Deployer
┏━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ STATUS │ UUID                                 │ PIPELINE_NAME                   │ PIPELINE_STEP_NAME                │ MODEL_NAME                     ┃
┠────────┼──────────────────────────────────────┼─────────────────────────────────┼───────────────────────────────────┼────────────────────────────────┨
┃   ✅   │ 0630b23b-431b-4a6a-9121-69d8036d8f24 │ pytorch_custom_code_pipeline    │ seldon_custom_model_deployer_step │ seldon-pytorch-custom-model    ┃
┠────────┼──────────────────────────────────────┼─────────────────────────────────┼───────────────────────────────────┼────────────────────────────────┨
┃   ✅   │ eaa6fc48-cda7-4c4e-8785-dc5b85cf0a31 │ tensorflow_custom_code_pipeline │ seldon_custom_model_deployer_step │ seldon-tensorflow-custom-model ┃
┗━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
# For the KServe Model Deployer
┏━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ STATUS │ UUID                                 │ PIPELINE_NAME                   │ PIPELINE_STEP_NAME                │ MODEL_NAME                     ┃
┠────────┼──────────────────────────────────────┼─────────────────────────────────┼───────────────────────────────────┼────────────────────────────────┨
┃   ✅   │ ed25e3f4-23f0-4e1d-b545-8531684ffbd5 │ pytorch_custom_code_pipeline    │ kserve_custom_model_deployer_step │ kserve-pytorch-custom-model    ┃
┠────────┼──────────────────────────────────────┼─────────────────────────────────┼───────────────────────────────────┼────────────────────────────────┨
┃   ✅   │ 617790f9-9592-411e-9e89-20e0dd1ea74a │ tensorflow_custom_code_pipeline │ kserve_custom_model_deployer_step │ kserve-tensorflow-custom-model ┃
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
┃ PIPELINE_RUN_ID        │ tensorflow_custom_code_pipeline-22_Aug_22-08_31_09_994315                                               ┃
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

To stop any prediction servers running in the background, use the `zenml model-server list`
and `zenml model-server delete <uuid>` CLI commands.:

```shell
zenml model-deployer models delete eaa6fc48-cda7-4c4e-8785-dc5b85cf0a31
```

Then delete the remaining ZenML references.

```shell
rm -rf zenml_examples
```

# 📜 Learn more

Our docs regarding the custom model deployment can be found [here](https://docs.zenml.io/mlops-stacks/model-deployers#custom-pre-processing-and-post-processing).

If you want to learn more about the deployment in ZenML in general or about how to build your deployer steps in ZenML
check out our [docs](https://docs.zenml.io/mlops-stacks/model-deployers/custom).
