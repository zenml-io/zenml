# Get up and running on AzureML

This example shows how you can use the `StepOperator` class to run your training 
jobs on AzureML.

AzureML offers specialized compute instances to run your training jobs and 
has a beautiful UI to track and manage your models and logs. You can now use 
ZenML to submit individual steps to be run on compute instances managed by 
AzureML.

## Overview
Here we train a simple sklearn classifier on the MNIST dataset on AzureML.

## Pre-requisites

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

## Installation

For the installation, you first need to install and initialize ZenML:

```bash
# Install ZenML
pip install zenml

# Install the required integrations
zenml integration install azureml sklearn

# Pull example
zenml example pull azureml_step_operator
cd zenml_examples/azureml_step_operator

# Initialize
zenml init
```

## Creating the stack
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

### Run your pipeline
Now we're ready. Execute:

```shell
python pipeline.py
```

### Clean up
In order to clean up, delete the remaining zenml references.

```shell
rm -rf zenml_examples
```