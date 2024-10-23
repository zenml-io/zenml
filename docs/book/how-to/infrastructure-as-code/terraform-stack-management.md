---
description: Registering Existing Infrastructure with ZenML: A Guide for Terraform Users
---

# Registering Existing Infrastructure with ZenML

Terraform is a powerful tool for managing infrastructure as code, and is by far the
most popular IaC tool. Many companies already have existing Terraform setups,
and it is often desirable to integrate ZenML with this setup.

We already got a glimpse on how to [deploy a cloud stack with Terraform](../stack-deployment/deploy-a-cloud-stack-with-terraform.md)
using existing Terraform modules that are maintained by the ZenML team. While this
is a great solution for quickly getting started, it might not always be suitable for
your use case.

This guide is for advanced users who want to manage their own custom Terraform code but
want to use ZenML to manage their stacks.

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

First, configure the REST API provider to communicate with your ZenML server:

```hcl
terraform {
  required_providers {
    restapi = {
      source  = "Mastercard/restapi"
      version = "~> 1.19"
    }
  }
}

provider "restapi" {
  alias                = "zenml_api"
  uri                  = var.zenml_server_url
  write_returns_object = true
  headers = {
    Authorization = "Bearer ${var.zenml_api_key}"
  }
}
```

### Service Connector Pattern

The key to successful registration is proper authentication. Service connectors are ZenML's way of managing this:

```hcl
# First, create a service connector
resource "restapi_object" "gcp_connector" {
  provider = restapi.zenml_api
  path     = "/api/v1/service-connectors"
  data = jsonencode({
    name = "gcp-${var.environment}-connector"
    type = "gcp"
    auth_method = "service-account"
    configuration = {
      project_id = var.project_id
      service_account_json = base64encode(var.service_account_key)
    }
  })
}

# Reference it in component registration
resource "restapi_object" "artifact_store" {
  provider = restapi.zenml_api
  path     = "/api/v1/stack-components"
  data = jsonencode({
    name = "existing-artifact-store"
    type = "artifact_store"
    flavor = "gcp"
    configuration = {
      path = "gs://${google_storage_bucket.ml_artifacts.name}"
    }
    service_connector_id = restapi_object.gcp_connector.id
  })
}
```

### Authentication Patterns

Different environments might need different authentication approaches:

```hcl
locals {
  auth_methods = {
    # Dev uses service account keys
    dev = {
      auth_method = "service-account"
      configuration = {
        service_account_json = base64encode(var.dev_sa_key)
      }
    }
    # Prod uses workload identity
    prod = {
      auth_method = "workload-identity"
      configuration = {
        workload_identity_pool = var.workload_identity_pool_id
        service_account = var.prod_service_account_email
      }
    }
  }
}

resource "restapi_object" "env_connector" {
  provider = restapi.zenml_api
  path     = "/api/v1/service-connectors"
  data = jsonencode({
    name = "${var.environment}-connector"
    type = "gcp"  # or aws/azure
    auth_method = local.auth_methods[var.environment].auth_method
    configuration = local.auth_methods[var.environment].configuration
  })
}
```

### Component Registration Patterns

Register different types of components:

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
        region = var.region
      }
    }
  }
}

# Register multiple components
resource "restapi_object" "stack_components" {
  for_each = local.component_configs
  
  provider = restapi.zenml_api
  path     = "/api/v1/stack-components"
  data = jsonencode(merge(
    each.value,
    {
      name = "existing-${each.key}"
      service_connector_id = restapi_object.env_connector.id
    }
  ))
}
```

### Creating the Stack

Finally, assemble the components into a stack:

```hcl
resource "restapi_object" "ml_stack" {
  provider = restapi.zenml_api
  path     = "/api/v1/stacks"
  
  data = jsonencode({
    name = "${var.environment}-ml-stack"
    components = {
      for k, v in restapi_object.stack_components : k => {
        id = v.id
      }
    }
  })
}
```

## Best Practices

1. **Service Connector Management**
   - Create one connector per environment/authentication method
   - Use workload identity in production when possible
   - Consider connector reuse across components

2. **Component Configuration**
   - Keep configurations DRY using locals
   - Use variables for environment-specific values
   - Document required configuration fields

3. **Stack Organization**
   - Group related components logically
   - Use consistent naming conventions
   - Consider component dependencies

4. **State Management**
   - Use separate state files for infrastructure and ZenML registration
   - Consider using workspaces for different environments
   - Keep registration state with the team that manages ML operations

Read more about best practices in the [next chapter](./terraform-best-practices.md).

## Practical Walkthrough: Registering Existing GCP Infrastructure

Let's walk through registering an ML infrastructure stack on GCP with ZenML. We'll assume you already have:
- A GCS bucket for artifacts
- An Artifact Registry repository
- A service account for ML operations
- Vertex AI enabled for orchestration

## Step 1: Create Registration Module

```hcl
# modules/zenml_gcp_registration/variables.tf
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
}

variable "artifact_store_bucket" {
  description = "Name of existing GCS bucket for artifacts"
  type        = string
}

variable "container_registry_id" {
  description = "Existing Artifact Registry repository ID"
  type        = string
}

variable "service_account_email" {
  description = "Email of the service account for ML operations"
  type        = string
}
```

## Step 2: Configure Provider and Service Connector

```hcl
# modules/zenml_gcp_registration/main.tf
terraform {
  required_providers {
    restapi = {
      source  = "Mastercard/restapi"
      version = "~> 1.19"
    }
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "restapi" {
  alias                = "zenml_api"
  uri                  = var.zenml_server_url
  write_returns_object = true
  headers = {
    Authorization = "Bearer ${var.zenml_api_key}"
  }
}

# Get service account key for the connector
data "google_service_account_key" "ml_sa_key" {
  name = "projects/${var.project_id}/serviceAccounts/${var.service_account_email}/keys/default"
}

# Create service connector for GCP authentication
resource "restapi_object" "gcp_connector" {
  provider = restapi.zenml_api
  path     = "/api/v1/service-connectors"
  data = jsonencode({
    name = "gcp-ml-connector"
    type = "gcp"
    auth_method = "service-account"
    configuration = {
      project_id = var.project_id
      service_account_json = data.google_service_account_key.ml_sa_key.private_key
    }
    resource_types = [
      "artifact-store",
      "container-registry",
      "orchestrator",
      "step-operator"
    ]
  })
}
```

## Step 3: Register Stack Components

```hcl
# modules/zenml_gcp_registration/components.tf

# Register artifact store
resource "restapi_object" "artifact_store" {
  provider = restapi.zenml_api
  path     = "/api/v1/stack-components"
  data = jsonencode({
    name = "gcp-artifact-store"
    type = "artifact_store"
    flavor = "gcp"
    configuration = {
      path = "gs://${var.artifact_store_bucket}"
    }
    service_connector_id = restapi_object.gcp_connector.id
  })
}

# Register container registry
resource "restapi_object" "container_registry" {
  provider = restapi.zenml_api
  path     = "/api/v1/stack-components"
  data = jsonencode({
    name = "gcp-container-registry"
    type = "container_registry"
    flavor = "gcp"
    configuration = {
      uri = "${var.region}-docker.pkg.dev/${var.project_id}/${var.container_registry_id}"
    }
    service_connector_id = restapi_object.gcp_connector.id
  })
}

# Register Vertex AI orchestrator
resource "restapi_object" "orchestrator" {
  provider = restapi.zenml_api
  path     = "/api/v1/stack-components"
  data = jsonencode({
    name = "vertex-orchestrator"
    type = "orchestrator"
    flavor = "vertex"
    configuration = {
      project = var.project_id
      region = var.region
      service_account = var.service_account_email
    }
    service_connector_id = restapi_object.gcp_connector.id
  })
}

# Register Vertex AI step operator
resource "restapi_object" "step_operator" {
  provider = restapi.zenml_api
  path     = "/api/v1/stack-components"
  data = jsonencode({
    name = "vertex-step-operator"
    type = "step_operator"
    flavor = "vertex"
    configuration = {
      project = var.project_id
      region = var.region
      service_account = var.service_account_email
    }
    service_connector_id = restapi_object.gcp_connector.id
  })
}
```

## Step 4: Create the Stack

```hcl
# modules/zenml_gcp_registration/stack.tf
resource "restapi_object" "ml_stack" {
  provider = restapi.zenml_api
  path     = "/api/v1/stacks"
  
  data = jsonencode({
    name = "gcp-ml-stack"
    description = "GCP ML stack using existing infrastructure"
    
    components = {
      artifact_store = {
        id = restapi_object.artifact_store.id
      }
      container_registry = {
        id = restapi_object.container_registry.id
      }
      orchestrator = {
        id = restapi_object.orchestrator.id
      }
      step_operator = {
        id = restapi_object.step_operator.id
      }
    }
  })
}
```

## Step 5: Output Stack Information

```hcl
# modules/zenml_gcp_registration/outputs.tf
output "stack_id" {
  description = "ID of the created ZenML stack"
  value       = restapi_object.ml_stack.id
}

output "stack_name" {
  description = "Name of the created ZenML stack"
  value       = jsondecode(restapi_object.ml_stack.data).name
}

output "service_connector_id" {
  description = "ID of the created service connector"
  value       = restapi_object.gcp_connector.id
}
```

## Step 6: Use the Registration Module

```hcl
# main.tf in your root configuration
module "zenml_registration" {
  source = "./modules/zenml_gcp_registration"
  
  zenml_server_url = "https://your-zenml-server.com"
  zenml_api_key    = var.zenml_api_key
  
  project_id             = "your-gcp-project"
  region                 = "us-central1"
  artifact_store_bucket  = "existing-ml-artifacts"
  container_registry_id  = "existing-ml-containers"
  service_account_email  = "ml-service-account@your-project.iam.gserviceaccount.com"
}

output "stack_info" {
  value = {
    id   = module.zenml_registration.stack_id
    name = module.zenml_registration.stack_name
  }
}
```

## Usage

After applying this configuration:

1. Install required integrations:
```bash
zenml integration install gcp
```

2. Set the stack:
```bash
zenml stack set $(terraform output -raw stack_info.name)
```

3. Verify the configuration:
```bash
zenml stack describe
```

This example demonstrates how to register existing GCP infrastructure with ZenML while maintaining clean separation between infrastructure provisioning and ZenML registration. The same pattern can be adapted for AWS and Azure infrastructure.
