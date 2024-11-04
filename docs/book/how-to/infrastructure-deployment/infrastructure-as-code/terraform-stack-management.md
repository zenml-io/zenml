---
description: Registering Existing Infrastructure with ZenML - A Guide for Terraform Users
---

# Manage your stacks with Terraform

Terraform is a powerful tool for managing infrastructure as code, and is by far the
most popular IaC tool. Many companies already have existing Terraform setups,
and it is often desirable to integrate ZenML with this setup.

We already got a glimpse on how to [deploy a cloud stack with Terraform](../stack-deployment/deploy-a-cloud-stack-with-terraform.md)
using existing Terraform modules that are maintained by the ZenML team. While this
is a great solution for quickly getting started, it might not always be suitable for
your use case.

This guide is for advanced users who want to manage their own custom Terraform code but
want to use ZenML to manage their stacks. For this, the
[ZenML provider](https://registry.terraform.io/providers/zenml-io/zenml/latest) is a better choice.

## Understanding the Two-Phase Approach

When working with ZenML stacks, there are two distinct phases:
1. **Infrastructure Deployment**: Creating cloud resources (typically handled by platform teams)
2. **ZenML Registration**: Registering these resources as ZenML stack components

While our official modules ([`zenml-stack/aws`](https://registry.terraform.io/modules/zenml-io/zenml-stack/aws/latest), [`zenml-stack/gcp`](https://registry.terraform.io/modules/zenml-io/zenml-stack/gcp/latest), [`zenml-stack/azure`](https://registry.terraform.io/modules/zenml-io/zenml-stack/azure/latest)) handle both phases, you might already have infrastructure deployed. Let's explore how to register existing infrastructure with ZenML.

## Phase 1: Infrastructure Deployment

You likely already have this handled in your existing Terraform configurations:

```hcl
# Example of existing GCP infrastructure
resource "google_storage_bucket" "ml_artifacts" {
  name     = "company-ml-artifacts"
  location = "US"
}

resource "google_artifact_registry_repository" "ml_containers" {
  repository_id = "ml-containers"
  format        = "DOCKER"
}
```

## Phase 2: ZenML Registration

### Setup the ZenML Provider

First, configure the [ZenML provider](https://registry.terraform.io/providers/zenml-io/zenml/latest) to communicate with your ZenML server:

```hcl
terraform {
  required_providers {
    zenml = {
      source = "zenml-io/zenml"
    }
  }
}

provider "zenml" {
  # Configuration options will be loaded from environment variables:
  # ZENML_SERVER_URL
  # ZENML_API_KEY
}
```

To generate a API key, use the command:

```bash
zenml service-account create <SERVICE_ACCOUNT_NAME>
```

You can learn more about how to generate a ZENML_API_KEY via service accounts
[here](../../project-setup-and-management/connecting-to-zenml/connect-with-a-service-account.md).

### Create the service connectors

The key to successful registration is proper authentication between the components.
[Service connectors](../auth-management/README.md) are ZenML's way of managing this:

```hcl
# First, create a service connector
resource "zenml_service_connector" "gcp_connector" {
  name        = "gcp-${var.environment}-connector"
  type        = "gcp"
  auth_method = "service-account"
  
  resource_types = ["artifact-store", "container-registry"]
  
  configuration = {
    project_id = var.project_id
  }
  
  secrets = {
    service_account_json = file("service-account.json")
  }
}

# Create a stack component referencing the connector
resource "zenml_stack_component" "artifact_store" {
  name   = "existing-artifact-store"
  type   = "artifact_store"
  flavor = "gcp"
  
  configuration = {
    path = "gs://${google_storage_bucket.ml_artifacts.name}"
  }
  
  connector_id = zenml_service_connector.gcp_connector.id
}
```

### Register the stack components

Register different types of [components](../../../component-guide/README.md):

```hcl
# Generic component registration pattern
locals {
  component_configs = {
    artifact_store = {
      type = "artifact_store"
      flavor = "gcp"
      configuration = {
        path = "gs://${google_storage_bucket.ml_artifacts.name}"
      }
    }
    container_registry = {
      type = "container_registry"
      flavor = "gcp"
      configuration = {
        uri = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.ml_containers.repository_id}"
      }
    }
    orchestrator = {
      type = "orchestrator"
      flavor = "vertex"
      configuration = {
        project = var.project_id
        region  = var.region
      }
    }
  }
}

# Register multiple components
resource "zenml_stack_component" "components" {
  for_each = local.component_configs
  
  name          = "existing-${each.key}"
  type          = each.value.type
  flavor        = each.value.flavor
  configuration = each.value.configuration
  
  connector_id = zenml_service_connector.env_connector.id
}
```

### Assemble the stack

Finally, assemble the components into a stack:

```hcl
resource "zenml_stack" "ml_stack" {
  name = "${var.environment}-ml-stack"
  
  components = {
    for k, v in zenml_stack_component.components : k => v.id
  }
}
```

## Practical Walkthrough: Registering Existing GCP Infrastructure

Let's see a complete example of registering an existing GCP infrastructure stack with ZenML.

### Prerequisites

- A GCS bucket for artifacts
- An Artifact Registry repository
- A service account for ML operations
- Vertex AI enabled for orchestration

### Step 1: Variables Configuration

```hcl
# variables.tf
variable "zenml_server_url" {
  description = "URL of the ZenML server"
  type        = string
}

variable "zenml_api_key" {
  description = "API key for ZenML server authentication"
  type        = string
  sensitive   = true
}

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Environment name (e.g., dev, staging, prod)"
  type        = string
}

variable "gcp_service_account_key" {
  description = "GCP service account key in JSON format"
  type        = string
  sensitive   = true
}
```

### Step 2: Main Configuration

```hcl
# main.tf
terraform {
  required_providers {
    zenml = {
      source = "zenml-io/zenml"
    }
    google = {
      source = "hashicorp/google"
    }
  }
}

# Configure providers
provider "zenml" {
  server_url = var.zenml_server_url
  api_key    = var.zenml_api_key
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Create GCP resources if needed
resource "google_storage_bucket" "artifacts" {
  name     = "${var.project_id}-zenml-artifacts-${var.environment}"
  location = var.region
}

resource "google_artifact_registry_repository" "containers" {
  location      = var.region
  repository_id = "zenml-containers-${var.environment}"
  format        = "DOCKER"
}

# ZenML Service Connector for GCP
resource "zenml_service_connector" "gcp" {
  name        = "gcp-${var.environment}"
  type        = "gcp"
  auth_method = "service-account"

  resource_types = [
    "artifact-store",
    "container-registry",
    "orchestrator",
    "step-operator"
  ]

  configuration = {
    project_id = var.project_id
    region     = var.region
  }

  secrets = {
    service_account_json = var.gcp_service_account_key
  }

  labels = {
    environment = var.environment
    managed_by  = "terraform"
  }
}

# Artifact Store Component
resource "zenml_stack_component" "artifact_store" {
  name   = "gcs-${var.environment}"
  type   = "artifact_store"
  flavor = "gcp"

  configuration = {
    path = "gs://${google_storage_bucket.artifacts.name}/artifacts"
  }

  connector_id = zenml_service_connector.gcp.id

  labels = {
    environment = var.environment
  }
}

# Container Registry Component
resource "zenml_stack_component" "container_registry" {
  name   = "gcr-${var.environment}"
  type   = "container_registry"
  flavor = "gcp"

  configuration = {
    uri = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.containers.repository_id}"
  }

  connector_id = zenml_service_connector.gcp.id

  labels = {
    environment = var.environment
  }
}

# Vertex AI Orchestrator
resource "zenml_stack_component" "orchestrator" {
  name   = "vertex-${var.environment}"
  type   = "orchestrator"
  flavor = "vertex"

  configuration = {
    location    = var.region
    synchronous = true
  }

  connector_id = zenml_service_connector.gcp.id

  labels = {
    environment = var.environment
  }
}

# Complete Stack
resource "zenml_stack" "gcp_stack" {
  name = "gcp-${var.environment}"

  components = {
    artifact_store     = zenml_stack_component.artifact_store.id
    container_registry = zenml_stack_component.container_registry.id
    orchestrator      = zenml_stack_component.orchestrator.id
  }

  labels = {
    environment = var.environment
    managed_by  = "terraform"
  }
}
```

### Step 3: Outputs Configuration

```hcl
# outputs.tf
output "stack_id" {
  description = "ID of the created ZenML stack"
  value       = zenml_stack.gcp_stack.id
}

output "stack_name" {
  description = "Name of the created ZenML stack"
  value       = zenml_stack.gcp_stack.name
}

output "artifact_store_path" {
  description = "GCS path for artifacts"
  value       = "${google_storage_bucket.artifacts.name}/artifacts"
}

output "container_registry_uri" {
  description = "URI of the container registry"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.containers.repository_id}"
}
```

### Step 4: terraform.tfvars Configuration

Create a `terraform.tfvars` file (remember to never commit this to version control):

```hcl
zenml_server_url = "https://your-zenml-server.com"
project_id       = "your-gcp-project-id"
region           = "us-central1"
environment      = "dev"
```

Store sensitive variables in environment variables:
```bash
export TF_VAR_zenml_api_key="your-zenml-api-key"
export TF_VAR_gcp_service_account_key=$(cat path/to/service-account-key.json)
```

### Usage Instructions

1. Install required providers and initializing Terraform:
```bash
terraform init
```

2. Install required ZenML integrations:
```bash
zenml integration install gcp
```

3. Review the planned changes:
```bash
terraform plan
```

4. Apply the configuration:
```bash
terraform apply
```

5. Set the newly created stack as active:
```bash
zenml stack set $(terraform output -raw stack_name)
```

6. Verify the configuration:
```bash
zenml stack describe
```

This complete example demonstrates:
- Setting up necessary GCP infrastructure
- Creating a service connector with proper authentication
- Registering stack components with the infrastructure
- Creating a complete ZenML stack
- Proper variable management and output configuration
- Best practices for sensitive information handling

The same pattern can be adapted for AWS and Azure infrastructure by adjusting the provider configurations and resource types accordingly.

Remember to:
- Use appropriate IAM roles and permissions
- Follow your organization's security practices for handling credentials
- Consider using Terraform workspaces for managing multiple environments
- Regular backup of your Terraform state files
- Version control your Terraform configurations (excluding sensitive files)