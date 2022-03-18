# Get up and running quickly on Sagemaker
This example shows how you can use the `StepOperator` class to run your training jobs on Sagemaker.

Sagemaker offers specialised compute instances to run your training jobs and has a beautiful UI to track and manage your models and logs. You can now use ZenML to submit individual steps to be run on compute instances managed by Amazon Sagemaker. 

## Overview
Here we train a simple sklearn classifier on the MNIST dataset using Amazon Sagemaker.

## Run it locally

Currently, step operators only work with a local orchestrator but support for cloud orchestrators is on the way soon!

### Installation
In order to run this example, you need to install and initialize ZenML and the necessary integrations:

```shell
# install CLI
pip install zenml

# install ZenML integrations
zenml integration install aws sklearn 

# pull example
zenml example pull sagemaker_step_resource
cd zenml_examples/sagemaker_step_resource

# initialize
zenml init
```

### Pre-requisites

In order to run the example, you need to setup a few things to allow ZenML to interact with GCP.

* First, you should create a service account

* Next, you need to choose what instance type needs to be used to run your jobs. You can get the list [here]()

* You can choose an GCP bucket to which Sagemaker should output any artifacts from your training run. 

* You can also choose a custom docker image that you want ZenML to use as a base image for creating an environment to run your jobs on Vertex AI. 

* You need to have the `gcp` cli set up with the right credentials. Make sure you have the permissions to create and manage Vertex AI custom jobs. 

* A container registry has to be configured in the stack. This registry will be used by ZenML to push your job images that Vertex will use. Check out the [cloud guide](https://docs.zenml.io/features/cloud-pipelines/guide-aws-gcp-azure) to learn how you can set up an GCP container registry. 

Once you have all these values handy, you can proceed to setting up the components required for your stack.

### Creating the stack

The stack will consist of:
- The local metadata store
- The local orchestrator
- An GCP artifact store
- The Vertex AI step operator

```bash

zenml artifact-store register gcp-store \
    --type=gcp
    --path=$PATH_TO_YOUR_GCS_BUCKET

# create the vertex step operator
zenml step-operator register vertex-step-operator \
    --type=vertex \
    --project=zenml-core \
    --region=eu-west1 \
    --machine_type=n1-standard-4 \
    --base_image=<CUSTOM_BASE_IMAGE>
    --bucket_name=<S3_BUCKET_NAME>
    --experiment_name=<SAGEMAKER_EXPERIMENT_NAME>

# register the container registry
zenml container-registry register gcr_registry --type=default --uri=<ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com

# register the sagemaker stack
zenml stack register vertex_training_stack \
    -m local_metadata_store \
    -o local_orchestrator \
    -c gcr_registry \
    -a gcs-store \
    -s vertex-step-operator

# activate the stack
zenml stack set vertex_training_stack
```

### Run the project
Now we're ready. Execute:

```shell
python train_on_sagemaker.py
```


### Clean up
In order to clean up, delete the remaining zenml references.

```shell
rm -rf zenml_examples
```