---
description: A guide to create and use Azure stacks in ZenML
icon: microsoft
---

# Azure

This documentation outlines the Azure services supported by ZenML and explains various methods to deploy and configure an Azure-based ZenML stack.

## Azure Components Supported by ZenML

### AzureML Orchestrator

The AzureML orchestrator leverages Azure Machine Learning's Python SDK v2 to execute ZenML pipelines. For each ZenML step, it creates an AzureML CommandComponent and combines them into a pipeline. The orchestrator supports different compute modes such as serverless compute, compute instances and compute clusters.

The orchestrator also supports running pipelines on a schedule using Azure's JobSchedules with both cron expressions and intervals.

### Azure Blob Storage Artifact Store

The Azure Artifact Store uses Azure Blob Storage to store pipeline artifacts. It requires a storage account and container, accessible via URIs in the format `az://container-name` or `abfs://container-name`.

### Azure Container Registry

The Azure Container Registry component stores Docker images used by ZenML pipelines. It requires an Azure Container Registry instance with a URI in the format `<REGISTRY_NAME>.azurecr.io`.

### AzureML Step Operator

The AzureML step operator allows individual pipeline steps to run on AzureML compute instances. Like the orchestrator, it supports serverless compute, compute instances, and compute clusters with configurable resources.

## Authenticating through the Azure Service Connector

The Azure Service Connector facilitates authentication between ZenML stack components and Azure services. It offers several authentication methods:

* **Service Principal**: Uses a client ID, client secret, and tenant ID
* **Access Token**: Uses a temporary Azure access token
* **Managed Identity**: Uses Azure managed identities for authentication
* **CLI Authentication**: Uses the Azure CLI authentication context

One service connector can authenticate multiple stack components to various Azure resources, simplifying credential management and access control.

## Deployment Methods for Azure Stack

### 1. Terraform Deployment (Recommended)

The ZenML Azure Terraform module provides infrastructure-as-code deployment of a complete Azure stack:

```bash
# Clone the ZenML repository
git clone https://github.com/zenml-io/zenml.git
cd zenml/terraform/azure

# Initialize Terraform
terraform init

# Configure variables (modify terraform.tfvars or use command line)
terraform apply -var="resource_group_name=zenml-stack" -var="location=eastus"
```

After deployment, register the stack components:

```bash
# Register components using outputs from Terraform
zenml artifact-store register azure_artifact_store -f azure \
  --path=<TERRAFORM_OUTPUT_STORAGE_URI> \
  --connector <TERRAFORM_OUTPUT_CONNECTOR_ID>

zenml orchestrator register azure_orchestrator -f azureml \
  --subscription_id=<TERRAFORM_OUTPUT_SUBSCRIPTION_ID> \
  --resource_group=<TERRAFORM_OUTPUT_RESOURCE_GROUP> \
  --workspace=<TERRAFORM_OUTPUT_WORKSPACE_NAME> \
  --connector <TERRAFORM_OUTPUT_CONNECTOR_ID>

zenml container-registry register azure_container_registry -f azure \
  --uri=<TERRAFORM_OUTPUT_REGISTRY_URI> \
  --connector <TERRAFORM_OUTPUT_CONNECTOR_ID>

# Register the stack
zenml stack register azure_stack \
  -o azure_orchestrator \
  -a azure_artifact_store \
  -c azure_container_registry
```

### 2. Stack Wizard with Existing Resources

The Stack Wizard scans available Azure resources using a service connector and creates stack components from them:

```bash
# CLI approach
zenml stack register azure_stack -p azure

# Or access through the dashboard: Stacks -> New Stack -> "Use existing Cloud"
```

The wizard walks you through:

1. Authentication setup or service connector selection
2. Resource selection for each stack component
3. Stack creation and registration

For more details on the Stack Wizard, see the [Register a Cloud Stack](../infrastructure-deployment/stack-deployment/register-a-cloud-stack.md) documentation.

### 3. 1-Click Deployment

The 1-click deployment tool automatically provisions all required Azure resources:

```bash
# CLI approach
zenml deploy azure --resource-group=new-zenml-stack --location=eastus

# Or access through the dashboard: Stacks -> New Stack -> "Deploy new Cloud"
```

For more details on 1-Click Deployment, see the [Deploy a Cloud Stack](../infrastructure-deployment/stack-deployment/deploy-a-cloud-stack.md) documentation.

### 4. Manual Deployment

Deploy components manually by:

1. Creating a resource group and necessary Azure resources (storage account, container registry, AzureML workspace)
2. Creating a service principal with appropriate permissions
3. Registering a service connector with the service principal credentials
4. Registering individual stack components and connecting them to the service connector
5. Creating a stack from these components

```bash
# Register service connector
zenml service-connector register azure_connector --type azure \
  --auth-method service-principal \
  --client_secret=<CLIENT_SECRET> \
  --tenant_id=<TENANT_ID> \
  --client_id=<APPLICATION_ID>

# Register components
zenml artifact-store register azure_artifact_store -f azure \
  --path=az://<CONTAINER_NAME> \
  --connector azure_connector

zenml orchestrator register azure_orchestrator -f azureml \
  --subscription_id=<SUBSCRIPTION_ID> \
  --resource_group=<RESOURCE_GROUP> \
  --workspace=<WORKSPACE_NAME> \
  --connector azure_connector

zenml container-registry register azure_container_registry -f azure \
  --uri=<REGISTRY_NAME>.azurecr.io \
  --connector azure_connector

# Register stack
zenml stack register azure_stack \
  -o azure_orchestrator \
  -a azure_artifact_store \
  -c azure_container_registry
```

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
