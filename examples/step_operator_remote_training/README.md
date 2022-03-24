# Train models on remote environments

This example shows how you can use the `StepOperator` class to run your training jobs on remote backends.

The step operator defers the execution of individual steps in a pipeline to specialized runtime environments that are optimized for Machine Learning workloads.

## Overview
Here we train a simple sklearn classifier on the MNIST dataset using one of three step operators:

- AWS Sagemaker
- GCP Vertex AI
- Microsoft AzureML

## Run it locally

Currently, step operators only work with a local orchestrator but support for cloud orchestrators is on the way soon!

### Installation
In order to run this example, you need to install and initialize ZenML and the necessary integrations:

```shell
# install CLI
pip install zenml

# install ZenML integrations
zenml integration install aws sagemaker sklearn vertex gcp azure azureml

# pull example
zenml example pull step_operator_remote_training
cd zenml_examples/step_operator_remote_training

# initialize
zenml init
```

### Pre-requisites 

Each type of step operator has their own pre-requisites. Please jump to the section of 
the step operator you would like to run on:

#### Sagemaker
Sagemaker offers specialised compute instances to run your training jobs and has a beautiful UI to track and manage your models and logs. You can now use ZenML to submit individual steps to be run on compute instances managed by Amazon Sagemaker. 

In order to run the example, you need to setup a few things to allow ZenML to interact with Sagemaker.

* First, you need to create a role in the IAM console that you want the jobs running in Sagemaker to assume. This role should at least have the `AmazonS3FullAccess` and `AmazonSageMakerFullAccess` policies applied. Check [this link](https://docs.aws.amazon.com/sagemaker/latest/dg/sagemaker-roles.html#sagemaker-roles-create-execution-role) to learn how to create a role.

* Next, you need to choose what instance type needs to be used to run your jobs. You can get the list [here](https://docs.aws.amazon.com/sagemaker/latest/dg/notebooks-available-instance-types.html).

* Optionally, you can choose an S3 bucket to which Sagemaker should output any artifacts from your training run. 

* You can also supply an experiment name if you have one created already. Check [this guide](https://docs.aws.amazon.com/sagemaker/latest/dg/experiments-create.html) to know how. If not provided, the job runs would be independent.

* You can also choose a custom docker image that you want ZenML to use as a base image for creating an environment to run your jobs in Sagemaker. 

* You need to have the `aws` cli set up with the right credentials. Make sure you have the permissions to create and manage Sagemaker runs. 

* A container registry has to be configured in the stack. This registry will be used by ZenML to push your job images that Sagemaker will run. Check out the [cloud guide](https://docs.zenml.io/features/cloud-pipelines/guide-aws-gcp-azure) to learn how you can set up an elastic container registry. 

Once you have all these values handy, you can proceed to setting up the components required for your stack.

The stack will consist of:
- The local metadata store
- The local orchestrator
- An S3 artifact store
- The Sagemaker step operator

```bash
zenml artifact-store register s3-store \
    --type=s3
    --path=$PATH_TO_YOUR_S3_BUCKET

# create the sagemaker step operator
zenml step-operator register sagemaker \
    --type=sagemaker
    --role=<SAGEMAKER_ROLE> \
    --instance_type=<SAGEMAKER_INSTANCE_TYPE>
    --base_image=<CUSTOM_BASE_IMAGE>
    --bucket_name=<S3_BUCKET_NAME>
    --experiment_name=<SAGEMAKER_EXPERIMENT_NAME>

# register the container registry
zenml container-registry register ecr_registry --type=default --uri=<ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com

# register the sagemaker stack
zenml stack register sagemaker_stack \
    -m local_metadata_store \
    -o local_orchestrator \
    -c ecr_registry \
    -a s3-store \
    -s sagemaker

# activate the stack
zenml stack set sagemaker_stack
```

#### Microsoft AzureML

[AzureML](https://azure.microsoft.com/en-us/services/machine-learning/) 
offers specialized compute instances to run your training jobs and 
has a beautiful UI to track and manage your models and logs. You can now use 
ZenML to submit individual steps to be run on compute instances managed by 
AzureML.

In order to run this example, we have to set up a few things to allow ZenML to 
interact with AzureML:

* First, you require a `Machine learning` [resource on Azure](https://docs.microsoft.com/en-us/azure/machine-learning/quickstart-create-resources). 
If you don't already have one, you can create it through the `All resources` 
page on the Azure portal. 
* Once your resource is created, you can head over to the `Azure Machine 
Learning Studio` and [create a compute cluster](https://docs.microsoft.com/en-us/azure/machine-learning/quickstart-create-resources#cluster) 
to run your pipelines. 
* Next, you will need an `environment` for your pipelines. You can simply 
create one following the guide [here](https://docs.microsoft.com/en-us/azure/machine-learning/how-to-manage-environments-in-studio).
* Finally, we have to set up our artifact store. In order to do this, we need 
to [create a blob container](https://docs.microsoft.com/en-us/azure/storage/blobs/storage-quickstart-blobs-portal)
on Azure. 

Optionally, you can also create a [Service Principal for authentication](https://docs.microsoft.com/en-us/azure/developer/java/sdk/identity-service-principal-auth). 
This might especially be useful if you are planning to orchestrate your 
pipelines in a non-local setup such as Kubeflow where your local authentication 
won't be accessible. However, for the sake of simplicity, this is considered to 
be out of the scope of this example.

The stack will consist of: 

* The **local metadata store** which will track the configuration of your 
executions.
* The **local orchestrator** which will be executing your pipelines steps.
* The **azure artifact store** which will be responsible for storing the
artifacts of your pipeline.
* The **azureml step operator** which will be utilized to run the training step 
on Azure.

```bash
zenml artifact-store register azure_store \
    --type=azure \
    --path=<AZURE_BLOB_CONTAINER_PATH>

zenml step-operator register azureml \
    --type=azureml \
    --subscription_id=<AZURE_SUBSCRIPTION_ID> \
    --resource_group=<AZURE_RESOURCE_GROUP> \
    --workspace_name=<AZURE_WORKSPACE_NAME> \
    --compute_target_name=<AZURE_COMPUTE_TARGET_NAME> \
    --environment_name=<AZURE_ENVIRONMENT_NAME> 

zenml stack register azureml_stack \
    -m local_metadata_store \
    -o local_orchestrator \
    -a azure_store \
    -s azureml
    
zenml stack set azureml_stack
```


#### GCP Vertex AI

[Vertex AI](https://cloud.google.com/vertex-ai) offers specialised compute to run 
[custom training jobs](https://cloud.google.com/vertex-ai/docs/training/custom-training) 
and has a beautiful UI to track and manage your models and logs. You can now use ZenML to submit an individual step to 
run on a managed training job managed on Vertex AI. 

In order to run the example, you need to setup a few things to allow ZenML to interact with GCP.

* First, you should create a service account

* Next, you need to choose what instance type needs to be used to run your jobs. You can get the list [here]()

* You can choose an GCP bucket to which Vertex should output any artifacts from your training run. 

* You can also choose a custom docker image that you want ZenML to use as a base image for creating an environment to run your jobs on Vertex AI. 

* You need to have the `gcp` cli set up with the right credentials. Make sure you have the permissions to create and manage Vertex AI custom jobs. 

* A container registry has to be configured in the stack. This registry will be used by ZenML to push your job images that Vertex will use. Check out the [cloud guide](https://docs.zenml.io/features/cloud-pipelines/guide-aws-gcp-azure) to learn how you can set up an GCP container registry. 

Once you have all these values handy, you can proceed to setting up the components required for your stack.

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
zenml step-operator register vertex \
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
    -s vertex

# activate the stack
zenml stack set vertex_training_stack
```


### Run the project
Now we're ready. Execute:

```shell
python run.py --step_operator STEP_OPERATOR_TYPE  # can be aws, vertex, azureml
```


### Clean up
In order to clean up, delete the remaining zenml references.

```shell
rm -rf zenml_examples
```