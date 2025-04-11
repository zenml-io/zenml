---
description: A guide to create and use AWS stacks in ZenML
icon: aws
---

# AWS

This documentation outlines the AWS services supported by ZenML and explains various methods to deploy and configure an AWS-based ZenML stack.

## AWS Components Supported by ZenML

### SageMaker Orchestrator

The SageMaker orchestrator allows you to run ZenML pipelines on AWS SageMaker. It leverages the SageMaker Python SDK to create and manage pipeline jobs. For each ZenML step, it creates a SageMaker processing job or training job, depending on the step's requirements.

The orchestrator supports running pipelines on a schedule using Amazon EventBridge, allowing both cron expressions and intervals.

### S3 Artifact Store

The S3 Artifact Store uses Amazon S3 buckets to store pipeline artifacts. It provides versioning, access controls, and lifecycle management for your ML artifacts. Artifacts are accessible via URIs in the format `s3://bucket-name/path/to/artifact`.

### ECR Container Registry

The AWS Elastic Container Registry (ECR) component stores Docker images used by ZenML pipelines. It provides secure, scalable, and reliable container image storage with integration to other AWS services.

### ECS Step Operator

The ECS (Elastic Container Service) step operator allows individual pipeline steps to run on AWS ECS. It supports both Fargate and EC2 launch types, letting you choose between serverless or EC2-based compute resources.

### SageMaker Step Operator

The SageMaker step operator enables running individual pipeline steps on SageMaker Processing jobs. It offers specialized hardware options like GPUs for training and supports specific SageMaker features for ML tasks.

## Authenticating through the AWS Service Connector

The AWS Service Connector facilitates authentication between ZenML stack components and AWS services. It offers several authentication methods:

* **AWS profile**: Uses profiles from your local AWS credentials file
* **Access keys**: Uses AWS access key ID and secret access key
* **IAM role**: Assumes an IAM role for authentication
* **Session token**: Uses temporary session credentials

One service connector can authenticate multiple stack components to various AWS resources, simplifying credential management and access control.

## Deployment Methods for AWS Stack

### 1. Terraform Deployment (Recommended)

The ZenML AWS Terraform module provides infrastructure-as-code deployment of a complete AWS stack:

```bash
# Clone the ZenML repository
git clone https://github.com/zenml-io/zenml.git
cd zenml/terraform/aws

# Initialize Terraform
terraform init

# Configure variables (modify terraform.tfvars or use command line)
terraform apply -var="region=us-west-2" -var="prefix=zenml"
```

After deployment, register the stack components:

```bash
# Register components using outputs from Terraform
zenml artifact-store register aws_artifact_store -f s3 \
  --path=<TERRAFORM_OUTPUT_S3_BUCKET_URI> \
  --connector <TERRAFORM_OUTPUT_CONNECTOR_ID>

zenml container-registry register aws_container_registry -f aws \
  --uri=<TERRAFORM_OUTPUT_ECR_URI> \
  --connector <TERRAFORM_OUTPUT_CONNECTOR_ID>

zenml orchestrator register aws_orchestrator -f sagemaker \
  --region=<TERRAFORM_OUTPUT_REGION> \
  --connector <TERRAFORM_OUTPUT_CONNECTOR_ID>

# Register the stack
zenml stack register aws_stack \
  -o aws_orchestrator \
  -a aws_artifact_store \
  -c aws_container_registry
```

### 2. Stack Wizard with Existing Resources

The Stack Wizard scans available AWS resources using a service connector and creates stack components from them:

```bash
# CLI approach
zenml stack register aws_stack -p aws

# Or access through the dashboard: Stacks -> New Stack -> "Use existing Cloud"
```

The wizard walks you through:

1. Authentication setup or service connector selection
2. Resource selection for each stack component
3. Stack creation and registration

For more details on the Stack Wizard, see the [Register a Cloud Stack](../infrastructure-deployment/stack-deployment/register-a-cloud-stack.md) documentation.

### 3. 1-Click Deployment

The 1-click deployment tool automatically provisions all required AWS resources:

```bash
# CLI approach
zenml deploy aws --region us-west-2 --bucket-name zenml-artifacts

# Or access through the dashboard: Stacks -> New Stack -> "Deploy new Cloud"
```

For more details on 1-Click Deployment, see the [Deploy a Cloud Stack](../infrastructure-deployment/stack-deployment/deploy-a-cloud-stack.md) documentation.

### 4. Manual Deployment

Deploy components manually by:

1. Creating AWS resources (S3 bucket, ECR repository, IAM roles)
2. Creating a service connector with appropriate AWS credentials
3. Registering individual stack components and connecting them to the service connector
4. Creating a stack from these components

```bash
# Register service connector
zenml service-connector register aws_connector --type aws \
  --auth-method profile --profile=default

# Register components
zenml artifact-store register aws_artifact_store -f s3 \
  --path=s3://my-bucket \
  --connector aws_connector

zenml container-registry register aws_container_registry -f aws \
  --uri=<ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com \
  --connector aws_connector

zenml orchestrator register aws_orchestrator -f sagemaker \
  --region=<REGION> \
  --connector aws_connector

# Register stack
zenml stack register aws_stack \
  -o aws_orchestrator \
  -a aws_artifact_store \
  -c aws_container_registry
```

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
