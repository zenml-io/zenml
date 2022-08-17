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

## 📄 Prerequisites:

For the ZenML Seldon Core deployer to work, three basic things are required:

1. access to a Kubernetes cluster. The example accepts a `--kubernetes-context`
command line argument. This Kubernetes context needs to point to the Kubernetes
cluster where Seldon Core or KServe model servers will be deployed. If the context is not
explicitly supplied to the example, it defaults to using the locally active
context.

2. Seldon Core or KServe needs to be preinstalled and running in the target Kubernetes
cluster (read below for a brief explanation of how to do that).

3. models deployed with Seldon Core need to be stored in some form of
persistent shared storage that is accessible from the Kubernetes cluster where
Seldon Core or KServe is installed (e.g. AWS S3, GCS, Azure Blob Storage, etc.).

## Seldon Core / KServe Setup 

For custom code deployment to work, you need to have either a Seldon Core or KServe
deployed in a Kubernetes cluster. ZenML provides two ways to setup these tools:

1. A step-by-step guide on how to setup and deploy a Seldon Core deployment can be found
in the integration example.
    * [KServe deployment guide](https://github.com/zenml-io/zenml/tree/main/examples/kserve_deployment#installing-kserve-eg-in-an-gke-cluster)
    * [Seldon Core deployment guide](https://github.com/zenml-io/zenml/tree/main/examples/seldon_deployment#installing-seldon-core-eg-in-an-eks-cluster).

2. A Terraform based recipes to provision all the required resources. More information can be found in the 
[Open Source MLOps Stack Recipes](https://github.com/zenml-io/mlops-stacks).


Once we have a ready deployment environment, we can start the example.
We will split this into 2 main sections, one for KServe and one for Seldon Core.

## 📦 KServe Custom Code Deployment

Work in progress.

## 📦 Seldon Core Custom Code Deployment

Work in progress.

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

