---
description: >-
  Managing authentication to cloud services and resources with Service
  Connectors
icon: link
---

# Service Connectors

Service Connectors provide a unified way to handle authentication between ZenML and external services like cloud providers. They are a critical part of working with cloud-based stacks.

A service connector is an entity that:

1. Stores credentials and authentication configuration
2. Provides secure access to specific resources
3. Can be shared across multiple stack components
4. Manages permissions and access scopes

Think of service connectors as secure bridges between your ZenML stack components and external services.

## Why Use Service Connectors?

### The Authentication Challenge

Without service connectors, you would need to:
* Configure authentication separately for each stack component
* Handle different authentication methods for each cloud service
* Store and manage credentials manually
* Update credentials in multiple places when they change

Service connectors solve these problems by providing a single point of authentication that can be reused across your stack components.

### Key Benefits

* **Centralized Authentication**: Manage all your cloud credentials in one place
* **Credential Reuse**: Configure authentication once, use it with multiple components
* **Security**: Implement security best practices, minimize credential exposure, and reduce the risk of leaks
* **Resource Discovery**: Easily find available resources on your cloud accounts
* **Simplified Rotation**: Update credentials in one place when they change
* **Team Sharing**: Securely share access to resources within your team

### Supported Cloud Providers and Services

ZenML supports connectors for major cloud providers and services:

* **AWS**: For Amazon Web Services (S3, ECR, SageMaker, etc.)
* **GCP**: For Google Cloud Platform (GCS, GCR, Vertex AI, etc.)
* **Azure**: For Microsoft Azure (Blob Storage, ACR, AzureML, etc.)
* **Kubernetes**: For Kubernetes clusters
* **Other Services**: Docker registries, MLflow, etc.

Each connector type supports authentication methods specific to that service.

## Working with Service Connectors

### Creating and Managing Connectors

```bash
# Register a new connector
zenml service-connector register aws-dev \
    --type aws \
    --auth-method profile \
    --profile=dev-account

# List all connectors
zenml service-connector list

# Verify a connector works
zenml service-connector verify aws-dev
```

### Discovering Resources

A powerful feature of service connectors is resource discovery:

```bash
# List available resources through a connector
zenml service-connector list-resources aws-dev --resource-type s3-bucket
```

This helps you find existing resources when configuring stack components.

### Using Connectors with Stack Components

Connect components to services:

```bash
# Register a component with a connector
zenml artifact-store register s3-store \
    --type s3 \
    --bucket my-bucket \
    --connector aws-dev
```

## Best Practices

* **Use descriptive names** for connectors indicating their purpose or environment
* **Create separate connectors** for development, staging, and production
* **Apply least privilege** when configuring connector permissions
* **Regularly rotate credentials** for enhanced security
* **Document your connector configurations** for team knowledge sharing

## Next Steps

* Learn how to [deploy stacks](deployment.md) using service connectors
* Explore [authentication methods](https://docs.zenml.io/how-to/infrastructure-deployment/auth-management/service-connectors-guide) for different cloud providers 
* Understand how to [reference secrets in stack configuration](https://docs.zenml.io/how-to/infrastructure-deployment/stack-deployment/reference-secrets-in-stack-configuration)
