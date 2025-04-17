---
description: A guide to create and use GCP stacks in ZenML
icon: google
---

# GCP

This documentation outlines the Google Cloud Platform (GCP) services supported by ZenML and explains various methods to deploy and configure a GCP-based ZenML stack.

## GCP Components Supported by ZenML

### Vertex AI Orchestrator

The Vertex AI orchestrator enables running ZenML pipelines on Google Cloud's Vertex AI service. It leverages the Vertex AI SDK to create and manage pipeline jobs. For each ZenML step, it creates a Vertex AI component and combines them into a pipeline.

The orchestrator supports running pipelines on a schedule using Google Cloud Scheduler, with both cron expressions and intervals.

### GCS Artifact Store

The GCS Artifact Store uses Google Cloud Storage buckets to store pipeline artifacts. It provides versioning, access controls, and lifecycle management for your ML artifacts. Artifacts are accessible via URIs in the format `gs://bucket-name/path/to/artifact`.

### GCR Container Registry

The Google Container Registry (GCR) component stores Docker images used by ZenML pipelines. It provides secure, scalable, and reliable container image storage with integration to other Google Cloud services. Google Artifact Registry is also supported as a newer alternative to GCR.

### GCP Cloud Run Step Operator

The Cloud Run step operator allows individual pipeline steps to run on Google Cloud Run. It provides a serverless execution environment with automatic scaling and pay-per-use billing.

### Vertex AI Step Operator

The Vertex AI step operator enables running individual pipeline steps on Vertex AI custom training jobs. It supports specialized hardware like TPUs and GPUs, and integrates with other Vertex AI features.

## Authenticating through the GCP Service Connector

The GCP Service Connector facilitates authentication between ZenML stack components and Google Cloud services. It offers several authentication methods:

* **User account**: Uses gcloud credentials from your local environment
* **Service account key**: Uses a service account key JSON file
* **Service account impersonation**: Impersonates a service account using your credentials
* **Workload identity**: Uses Kubernetes workload identity for GCP authentication

One service connector can authenticate multiple stack components to various GCP resources, simplifying credential management and access control.

## Deployment Methods for GCP Stack

### 1. Terraform Deployment (Recommended)

The ZenML GCP Terraform module provides infrastructure-as-code deployment of a complete GCP stack:

```bash
# Clone the ZenML repository
git clone https://github.com/zenml-io/zenml.git
cd zenml/terraform/gcp

# Initialize Terraform
terraform init

# Configure variables (modify terraform.tfvars or use command line)
terraform apply -var="project=my-project" -var="region=us-central1" -var="prefix=zenml"
```

After deployment, register the stack components:

```bash
# Register components using outputs from Terraform
zenml artifact-store register gcp_artifact_store -f gcp \
  --path=<TERRAFORM_OUTPUT_GCS_BUCKET_URI> \
  --connector <TERRAFORM_OUTPUT_CONNECTOR_ID>

zenml container-registry register gcp_container_registry -f gcp \
  --uri=<TERRAFORM_OUTPUT_GCR_URI> \
  --connector <TERRAFORM_OUTPUT_CONNECTOR_ID>

zenml orchestrator register gcp_orchestrator -f vertex \
  --project=<TERRAFORM_OUTPUT_PROJECT> \
  --region=<TERRAFORM_OUTPUT_REGION> \
  --connector <TERRAFORM_OUTPUT_CONNECTOR_ID>

# Register the stack
zenml stack register gcp_stack \
  -o gcp_orchestrator \
  -a gcp_artifact_store \
  -c gcp_container_registry
```

### 2. Stack Wizard with Existing Resources

The Stack Wizard scans available GCP resources using a service connector and creates stack components from them:

```bash
# CLI approach
zenml stack register gcp_stack -p gcp

# Or access through the dashboard: Stacks -> New Stack -> "Use existing Cloud"
```

The wizard walks you through:

1. Authentication setup or service connector selection
2. Resource selection for each stack component
3. Stack creation and registration

For more details on the Stack Wizard, see the [Register a Cloud Stack](../infrastructure-deployment/stack-deployment/register-a-cloud-stack.md) documentation.

### 3. 1-Click Deployment

The 1-click deployment tool automatically provisions all required GCP resources:

```bash
# CLI approach
zenml deploy gcp --project my-project --region us-central1

# Or access through the dashboard: Stacks -> New Stack -> "Deploy new Cloud"
```

For more details on 1-Click Deployment, see the [Deploy a Cloud Stack](../infrastructure-deployment/stack-deployment/deploy-a-cloud-stack.md) documentation.

### 4. Manual Deployment

Deploy components manually by:

1. Creating GCP resources (GCS bucket, GCR repository, service accounts)
2. Creating a service connector with appropriate GCP credentials
3. Registering individual stack components and connecting them to the service connector
4. Creating a stack from these components

```bash
# Register service connector
zenml service-connector register gcp_connector --type gcp \
  --auth-method user-account

# Register components
zenml artifact-store register gcp_artifact_store -f gcp \
  --path=gs://my-bucket \
  --connector gcp_connector

zenml container-registry register gcp_container_registry -f gcp \
  --uri=gcr.io/my-project \
  --connector gcp_connector

zenml orchestrator register gcp_orchestrator -f vertex \
  --project=my-project \
  --region=us-central1 \
  --connector gcp_connector

# Register stack
zenml stack register gcp_stack \
  -o gcp_orchestrator \
  -a gcp_artifact_store \
  -c gcp_container_registry
```

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
