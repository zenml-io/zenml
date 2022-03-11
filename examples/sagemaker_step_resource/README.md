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

In order to run the example, you need to setup a few things to allow ZenML to interact with Sagemaker.

* First, you need to create a role in the IAM console that you want the jobs running in Sagemaker to assume. This role should at least have the `AmazonS3FullAccess` and `AmazonSageMakerFullAccess` policies applied. Check [this link](https://docs.aws.amazon.com/sagemaker/latest/dg/sagemaker-roles.html#sagemaker-roles-create-execution-role) to learn how to create a role.

* Next, you need to choose what instance type needs to be used to run your jobs. You can get the list [here](https://docs.aws.amazon.com/sagemaker/latest/dg/notebooks-available-instance-types.html).

* Optionally, you can choose an S3 bucket to which Sagemaker should output any artifacts from your training run. 

* You can also supply an experiment name if you have one created already. Check [this guide](https://docs.aws.amazon.com/sagemaker/latest/dg/experiments-create.html) to know how. If not provided, the job runs would be independent.

* You can also choose a custom docker image that you want ZenML to use as a base image for creating an environment to run your jobs in Sagemaker. 

* You need to have the `aws` cli set up with the right credentials. Make sure you have the permissions to create and manage Sagemaker runs. 

* A container registry has to be configured in the stack. This registry will be used by ZenML to push your job images that Sagemaker will run. Check out the [cloud guide](https://docs.zenml.io/features/cloud-pipelines/guide-aws-gcp-azure) to learn how you can set up an elastic container registry. 

Once you have all these values handy, you can proceed to setting up the components required for your stack.

### Creating the stack

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