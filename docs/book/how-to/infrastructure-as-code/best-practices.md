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

ZenML introduces stack components as abstractions over cloud resources. Let's explore how to architect this effectively with Terraform.

## Part 1: Foundation - Stack Component Architecture

### The Problem
Different teams need different ML infrastructure configurations, but you want to maintain consistency and reusability.

### The Solution: Component-Based Architecture

Start by breaking down your infrastructure into reusable modules that map to ZenML stack components:

```hcl
# modules/zenml_stack_base/main.tf
module "base_infrastructure" {
  source = "./modules/base_infra"
  
  environment = var.environment
  project_id  = var.project_id
  region      = var.region
  
  # Generate consistent naming across resources
  resource_prefix = "zenml-${var.environment}-${random_id.suffix.hex}"
}

# Create base stack components
resource "zenml_stack" "base_stack" {
  name        = "${var.environment}-base-stack"
  description = "Base infrastructure for ${var.environment}"

  components = {
    artifact_store = {
      flavor = "gcp"
      config = {
        path = module.base_infrastructure.artifact_store_path
      }
    }
    container_registry = {
      flavor = "gcp"
      config = {
        uri = module.base_infrastructure.container_registry_uri
      }
    }
  }
}
```

Now teams can extend this base stack:

```hcl
# team_configs/training_stack.tf
module "training_stack" {
  source = "./modules/specialized_stack"
  
  base_stack_id = zenml_stack.base_stack.id
  
  # Add training-specific components
  additional_components = {
    orchestrator = {
      flavor = "vertex"
      config = {
        machine_type = "n1-standard-8"
        gpu_enabled = true
      }
    }
  }
}
```

You can now register them with ZenML using the REST API provider (as demonstrated in this [official ZenML stack module](https://github.com/zenml-io/terraform-gcp-zenml-stack)):

```hcl
provider "restapi" {
  alias                = "zenml_api"
  uri                  = var.zenml_server_url
  write_returns_object = true
  headers = {
    Authorization = "Bearer ${var.zenml_api_key}"
  }
}

resource "restapi_object" "zenml_stack" {
  provider = restapi.zenml_api
  path     = "/api/v1/stacks"
  data = jsonencode({
    name        = "${var.environment}-base-stack"
    description = "Base infrastructure for ${var.environment}"
    components  = {
      artifact_store = {
        flavor = "gcp"
        configuration = {
          path = "gs://${google_storage_bucket.artifact_store.name}"
        }
      }
      container_registry = {
        flavor = "gcp"
        configuration = {
          uri = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.container_registry.repository_id}"
        }
      }
    }
  })
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
  auth_patterns = {
    dev = {
      method = "service-account"
      config = {
        type = "gcp"
        service_account_json = google_service_account_key.dev_sa.private_key
      }
    }
    prod = {
      method = "workload-identity"
      config = {
        type = "gcp"
        workload_identity_provider = google_iam_workload_identity_pool.prod.id
      }
    }
  }
}
```

Create service connectors and link them to stack components:

```hcl
# First create the service connector
resource "restapi_object" "gcp_connector" {
  provider = restapi.zenml_api
  path     = "/api/v1/service-connectors"
  data = jsonencode({
    name = "gcp-${var.environment}-connector"
    type = "gcp"
    auth_method = local.auth_patterns[var.environment].method
    configuration = local.auth_patterns[var.environment].config
  })
}

# Then reference it in your stack components
resource "restapi_object" "zenml_stack" {
  provider = restapi.zenml_api
  path     = "/api/v1/stacks"
  data = jsonencode({
    name = "${var.environment}-stack"
    components = {
      artifact_store = {
        flavor = "gcp"
        configuration = {
          path = "gs://${google_storage_bucket.artifact_store.name}"
        }
        service_connector_id = restapi_object.gcp_connector.id
      }
      # Other components...
    }
  })
}
```

## Part 3: Resource Sharing and Isolation

### The Problem

Different ML projects need to share some resources while maintaining isolation for others.

### The Solution: Resource Scoping Pattern

Implement a resource sharing strategy using path-based isolation:

```hcl
# shared_resources.tf
module "shared_artifact_store" {
  source = "./modules/artifact_store"
  
  # Shared configuration
  storage_class = "STANDARD"
  location      = var.region
  
  # Project-specific paths
  project_paths = {
    fraud_detection = "projects/fraud_detection/${var.environment}"
    recommendation  = "projects/recommendation/${var.environment}"
  }
}

# project_stack.tf
module "project_stack" {
  source = "./modules/project_stack"
  
  # Share the artifact store but with project-specific paths
  artifact_store_config = {
    bucket_name = module.shared_artifact_store.bucket_name
    base_path   = module.shared_artifact_store.project_paths[var.project_name]
  }
  
  # Project-specific container registry
  container_registry_config = {
    repository_id = "${var.project_name}-${var.environment}"
  }
}
```

Note: While this example uses project-based isolation, it's different from ZenML Pro's team feature, which manages user access control. This infrastructure-level isolation complements ZenML's built-in access controls.

## Part 4: Environment Management

### The Problem
Managing multiple environments while maintaining consistency and avoiding configuration drift.

### The Solution: Environment Configuration Pattern

Use Terraform workspaces and environment-specific configurations:

```hcl
# config/environments/prod.tfvars
environment = "prod"
stack_config = {
  high_availability = true
  backup_enabled    = true
  compliance_mode   = "strict"
}

# main.tf
module "environment_stack" {
  source = "./modules/environment_stack"
  
  # Base configuration
  stack_name = "zenml-${var.environment}"
  
  # Environment-specific overrides
  config = merge(
    local.default_config,
    var.stack_config
  )
}
```

## Best Practices and Lessons Learned

1. **Stack Component Versioning**
   - Version your stack components independently
   - Use semantic versioning for stack configurations
   ```hcl
   locals {
     stack_version = "1.2.0"
     stack_name    = "zenml-${var.environment}-v${local.stack_version}"
   }
   ```

2. **Resource Cleanup**
   - Use tags to track resource ownership and environment
   ```hcl
   locals {
     common_tags = {
       managed_by = "terraform"
       stack_id   = zenml_stack.main.id
       project    = var.project_name
     }
   }
   ```
   - Implement cleanup through Terraform destroy or cloud provider lifecycle policies
   - Consider using cloud provider native cleanup mechanisms (e.g., GCS bucket lifecycle rules) rather than expiration tags

3. **Stack Evolution**
   - Design for component upgrades
   - Maintain backward compatibility
   ```hcl
   resource "restapi_object" "zenml_stack" {
     provider = restapi.zenml_api
     path     = "/api/v1/stacks"
     
     lifecycle {
       create_before_destroy = true
       # Be careful with ignore_changes as stack updates might need
       # full replacement depending on the ZenML server version
       ignore_changes = [
         # Only ignore specific metadata that doesn't affect functionality
         data.labels,
         data.description
       ]
     }
   }
   ```

## Conclusion

Building ML infrastructure with ZenML and Terraform allows you to create a flexible, maintainable, and secure environment for ML teams. The key is to use ZenML's abstractions effectively while maintaining clean infrastructure patterns underneath.