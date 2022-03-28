# Train models on remote environments

This example shows how you can use the `StepOperator` class to run your training jobs on remote backends.

The step operator defers the execution of individual steps in a pipeline to specialized runtime environments that are optimized for Machine Learning workloads.

## Overview
Here we train a simple sklearn classifier on the MNIST dataset using one of three step operators:

- AWS Sagemaker
- GCP Vertex AI
- Microsoft AzureML

Currently, step operators only work with a local orchestrator but support for cloud orchestrators is on the way soon!

## Installation
In order to run this example, you need to install and initialize ZenML and the necessary integrations:

```shell
# install CLI
pip install zenml

# install ZenML integrations
zenml integration install aws s3 sagemaker sklearn vertex gcp azure azureml

# pull example
zenml example pull step_operator_remote_training
cd zenml_examples/step_operator_remote_training

# initialize
zenml init
```

## Pre-requisites 

Each type of step operator has their own pre-requisites. 

Before running this example, you must set up the individual cloud providers in a certain way. The complete guide can be found in the [docs](https://docs.zenml.io/features/step-operators).

Please jump to the section of 
the step operator you would like to run on:

### Sagemaker
Sagemaker offers specialized compute instances to run your training jobs and has a beautiful UI to track and manage your models and logs. You can now use ZenML to submit individual steps to be run on compute instances managed by Amazon Sagemaker. 

The stack will consist of:
* The **local metadata store** which will track the configuration of your 
executions.
* The **local orchestrator** which will be executing your pipelines steps.
* An **S3 artifact store** which will be responsible for storing the
artifacts of your pipeline.
* The **Sagemaker step operator** which will be utilized to run the training step on Sagemaker.

To configure resources for the step operators, please follow [this guide](https://docs.zenml.io/features/step-operators) and then proceed with the following steps:

```bash
zenml artifact-store register s3-store \
    --type=s3
    --path=<S3_BUCKET_PATH>

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

### Microsoft AzureML

[AzureML](https://azure.microsoft.com/en-us/services/machine-learning/) 
offers specialized compute instances to run your training jobs and 
has a beautiful UI to track and manage your models and logs. You can now use 
ZenML to submit individual steps to be run on compute instances managed by 
AzureML.

The stack will consist of: 

* The **local metadata store** which will track the configuration of your 
executions.
* The **local orchestrator** which will be executing your pipelines steps.
* An **azure artifact store** which will be responsible for storing the
artifacts of your pipeline.
* The **azureml step operator** which will be utilized to run the training step on Azure.

To configure resources for the step operators, please follow [this guide](https://docs.zenml.io/features/step-operators) and then proceed with the following steps:

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

### GCP Vertex AI

[Vertex AI](https://cloud.google.com/vertex-ai) offers specialized compute to run 
[custom training jobs](https://cloud.google.com/vertex-ai/docs/training/custom-training) 
and has a beautiful UI to track and manage your models and logs. You can now use ZenML to submit an individual step to 
run on a managed training job managed on Vertex AI. 

The stack will consist of:
* The **local metadata store** which will track the configuration of your 
executions.
* The **local orchestrator** which will be executing your pipelines steps.
* A **GCP Bucket artifact store** which will be responsible for storing the
artifacts of your pipeline.
* The **Vertex AI step operator** which will be utilized to run the training step 
on GCP.

To configure resources for the step operators, please follow [this guide](https://docs.zenml.io/features/step-operators) and then proceed with the following steps:

```bash
zenml artifact-store register gcp-store \
    --type=gcp
    --path=<GCS_BUCKET_PATH>

# create the vertex step operator
zenml step-operator register vertex \
    --type=vertex \
    --project=zenml-core \
    --region=eu-west1 \
    --machine_type=n1-standard-4 \
    --base_image=<CUSTOM_BASE_IMAGE>
    --accelerator_type=...

# register the container registry
zenml container-registry register gcr_registry --type=default --uri=gcr.io/<PROJECT-ID>/<IMAGE>

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
python run.py --step_operator <STEP_OPERATOR_TYPE>  # can be sagemaker, vertex, azureml
```


### Clean up
In order to clean up, delete the remaining zenml references.

```shell
rm -rf zenml_examples
```
