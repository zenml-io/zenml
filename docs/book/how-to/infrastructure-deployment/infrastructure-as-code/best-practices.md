---
description: Best practices for using IaC with ZenML
---

# Architecting ML Infrastructure with ZenML and Terraform

## The Challenge

You're a system architect tasked with setting up a scalable ML infrastructure that needs to:
- Support multiple ML teams with different requirements
- Work across multiple environments (dev, staging, prod)
- Maintain security and compliance standards
- Allow teams to iterate quickly without infrastructure bottlenecks

## The ZenML Approach

ZenML introduces stack components as abstractions over cloud resources. Let's explore how to architect this effectively with Terraform using the official ZenML provider.

## Part 1: Foundation - Stack Component Architecture

### The Problem
Different teams need different ML infrastructure configurations, but you want to maintain consistency and reusability.

### The Solution: Component-Based Architecture

Start by breaking down your infrastructure into reusable modules that map to ZenML stack components:

```hcl
# modules/zenml_stack_base/main.tf
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

# Create base infrastructure
module "base_infrastructure" {
  source = "./modules/base_infra"
  
  environment = var.environment
  project_id  = var.project_id
  region      = var.region
  
  # Generate consistent naming across resources
  resource_prefix = "zenml-${var.environment}-${random_id.suffix.hex}"
}

# Create service connector for authentication
resource "zenml_service_connector" "base_connector" {
  name        = "${var.environment}-base-connector"
  type        = "gcp"
  auth_method = "service-account"

  resource_types = [
    "artifact-store",
    "container-registry"
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
  }
}

# Create base stack components
resource "zenml_stack_component" "artifact_store" {
  name   = "${var.environment}-artifact-store"
  type   = "artifact_store"
  flavor = "gcp"

  configuration = {
    path = "gs://${module.base_infrastructure.artifact_store_bucket}/artifacts"
  }

  connector_id = zenml_service_connector.base_connector.id
}

resource "zenml_stack_component" "container_registry" {
  name   = "${var.environment}-container-registry"
  type   = "container_registry"
  flavor = "gcp"

  configuration = {
    uri = "${var.region}-docker.pkg.dev/${var.project_id}/${module.base_infrastructure.container_registry_id}"
  }

  connector_id = zenml_service_connector.base_connector.id
}

# Create the base stack
resource "zenml_stack" "base_stack" {
  name = "${var.environment}-base-stack"

  components = {
    artifact_store     = zenml_stack_component.artifact_store.id
    container_registry = zenml_stack_component.container_registry.id
  }

  labels = {
    environment = var.environment
    type        = "base"
  }
}
```

Teams can extend this base stack:

```hcl
# team_configs/training_stack.tf

# Create training-specific connector
resource "zenml_service_connector" "training_connector" {
  name        = "${var.environment}-training-connector"
  type        = "gcp"
  auth_method = "service-account"

  resource_types = ["orchestrator"]

  configuration = {
    project_id = var.project_id
    region     = var.region
  }

  secrets = {
    service_account_json = var.gcp_service_account_key
  }
}

# Add training-specific components
resource "zenml_stack_component" "training_orchestrator" {
  name   = "${var.environment}-training-orchestrator"
  type   = "orchestrator"
  flavor = "vertex"

  configuration = {
    location      = var.region
    machine_type  = "n1-standard-8"
    gpu_enabled   = true
    synchronous   = true
  }

  connector_id = zenml_service_connector.training_connector.id
}

# Create specialized training stack
resource "zenml_stack" "training_stack" {
  name = "${var.environment}-training-stack"

  components = {
    artifact_store     = zenml_stack_component.artifact_store.id
    container_registry = zenml_stack_component.container_registry.id
    orchestrator       = zenml_stack_component.training_orchestrator.id
  }

  labels = {
    environment = var.environment
    type        = "training"
  }
}
```

## Part 2: Authentication and Access Control

### The Problem
Different environments require different authentication methods, and you need to maintain security without complexity.

### The Solution: Smart Service Connector Pattern

Create a flexible service connector setup that adapts to your environment:

```hcl
locals {
  # Define authentication patterns per environment
  auth_config = {
    dev = {
      auth_method = "service-account"
      secrets = {
        service_account_json = file("dev-sa.json")
      }
    }
    prod = {
      auth_method = "workload-identity"
      configuration = {
        workload_identity_pool = var.workload_identity_pool_id
        service_account       = var.prod_service_account_email
      }
    }
  }
}

# Create environment-specific connector
resource "zenml_service_connector" "env_connector" {
  name        = "${var.environment}-connector"
  type        = "gcp"
  auth_method = local.auth_config[var.environment].auth_method

  resource_types = [
    "artifact-store",
    "container-registry",
    "orchestrator"
  ]

  dynamic "configuration" {
    for_each = try(local.auth_config[var.environment].configuration, {})
    content {
      key   = configuration.key
      value = configuration.value
    }
  }

  dynamic "secrets" {
    for_each = try(local.auth_config[var.environment].secrets, {})
    content {
      key   = secrets.key
      value = secrets.value
    }
  }
}
```

## Part 3: Resource Sharing and Isolation

### The Problem
Different ML projects need to share some resources while maintaining isolation for others.

### The Solution: Resource Scoping Pattern

Implement resource sharing with project isolation:

```hcl
locals {
  project_paths = {
    fraud_detection = "projects/fraud_detection/${var.environment}"
    recommendation  = "projects/recommendation/${var.environment}"
  }
}

# Create shared artifact store components with project isolation
resource "zenml_stack_component" "project_artifact_stores" {
  for_each = local.project_paths
  
  name   = "${each.key}-artifact-store"
  type   = "artifact_store"
  flavor = "gcp"
  
  configuration = {
    path = "gs://${var.shared_bucket}/${each.value}"
  }
  
  connector_id = zenml_service_connector.env_connector.id
  
  labels = {
    project     = each.key
    environment = var.environment
  }
}

# Create project-specific stacks
resource "zenml_stack" "project_stacks" {
  for_each = local.project_paths
  
  name = "${each.key}-stack"
  
  components = {
    artifact_store = zenml_stack_component.project_artifact_stores[each.key].id
  }
  
  labels = {
    project     = each.key
    environment = var.environment
  }
}
```

## Part 4: Environment Management

### The Solution: Environment Configuration Pattern

Use environment-specific configurations:

```hcl
locals {
  env_config = {
    dev = {
      machine_type = "n1-standard-4"
      gpu_enabled  = false
    }
    prod = {
      machine_type = "n1-standard-8"
      gpu_enabled  = true
    }
  }
}

# Create environment-specific orchestrator
resource "zenml_stack_component" "env_orchestrator" {
  name   = "${var.environment}-orchestrator"
  type   = "orchestrator"
  flavor = "vertex"
  
  configuration = merge(
    {
      location = var.region
    },
    local.env_config[var.environment]
  )
  
  connector_id = zenml_service_connector.env_connector.id
  
  labels = {
    environment = var.environment
  }
}
```

## Best Practices and Lessons Learned

1. **Stack Component Versioning**
```hcl
locals {
  stack_version = "1.2.0"
  common_labels = {
    version     = local.stack_version
    managed_by  = "terraform"
    environment = var.environment
  }
}

resource "zenml_stack" "versioned_stack" {
  name   = "stack-v${local.stack_version}"
  labels = local.common_labels
}
```

2. **Service Connector Management**
```hcl
# Create environment-specific connectors with clear purposes
resource "zenml_service_connector" "env_connector" {
  name        = "${var.environment}-${var.purpose}-connector"
  type        = var.connector_type
  
  # Use workload identity for production
  auth_method = var.environment == "prod" ? "workload-identity" : "service-account"
  
  # Enable connector reuse across components
  resource_types = var.supported_resources
  
  labels = merge(local.common_labels, {
    purpose = var.purpose
  })
}
```

3. **Component Configuration Management**
```hcl
# Define reusable configurations
locals {
  base_configs = {
    orchestrator = {
      location = var.region
      project  = var.project_id
    }
    artifact_store = {
      path_prefix = "gs://${var.bucket_name}"
    }
  }
  
  # Environment-specific overrides
  env_configs = {
    dev = {
      orchestrator = {
        machine_type = "n1-standard-4"
      }
    }
    prod = {
      orchestrator = {
        machine_type = "n1-standard-8"
      }
    }
  }
}

resource "zenml_stack_component" "configured_component" {
  name   = "${var.environment}-${var.component_type}"
  type   = var.component_type
  
  # Merge configurations
  configuration = merge(
    local.base_configs[var.component_type],
    try(local.env_configs[var.environment][var.component_type], {})
  )
}
```

4. **Stack Organization and Dependencies**
```hcl
# Group related components with clear dependency chains
module "ml_stack" {
  source = "./modules/ml_stack"
  
  depends_on = [
    module.base_infrastructure,
    module.security
  ]
  
  components = {
    # Core components
    artifact_store     = module.storage.artifact_store_id
    container_registry = module.container.registry_id
    
    # Optional components based on team needs
    orchestrator       = var.needs_orchestrator ? module.compute.orchestrator_id : null
    experiment_tracker = var.needs_tracking ? module.mlflow.tracker_id : null
  }
  
  labels = merge(local.common_labels, {
    stack_type = "ml-platform"
  })
}
```

5. **State Management**
```hcl
terraform {
  backend "gcs" {
    prefix = "terraform/state"
  }
  
  # Separate state files for infrastructure and ZenML
  workspace_prefix = "zenml-"
}

# Use data sources to reference infrastructure state
data "terraform_remote_state" "infrastructure" {
  backend = "gcs"
  
  config = {
    bucket = var.state_bucket
    prefix = "terraform/infrastructure"
  }
}
```

These practices help maintain a clean, scalable, and maintainable infrastructure codebase while following infrastructure-as-code best practices. Remember to:

- Keep configurations DRY using locals and variables
- Use consistent naming conventions across resources
- Document all required configuration fields
- Consider component dependencies when organizing stacks
- Separate infrastructure and ZenML registration state
- Use workspaces for different environments
- Keep registration state with the ML operations team

## Conclusion

Building ML infrastructure with ZenML and Terraform enables you to create a flexible, maintainable, and secure environment for ML teams. The official ZenML provider simplifies the process while maintaining clean infrastructure patterns.