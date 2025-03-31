---
description: Managing authentication to cloud services and resources with Service Connectors
---

# Service Connectors

Service Connectors in ZenML provide a unified way to authenticate and connect to external services and resources. They abstract away the complexity of handling different authentication methods across various cloud providers and services.

## Understanding Service Connectors

A service connector is an entity that:

1. Stores credentials and authentication configuration
2. Provides access to specific resources through those credentials 
3. Can be shared across multiple stack components
4. Manages permissions and access scopes

Service connectors separate authentication concerns from resource usage, making it easier to manage credentials and permissions across your ML infrastructure.

## Key Benefits

### Simplified Authentication

Service connectors handle the complexities of various authentication methods (API keys, OAuth tokens, IAM roles, etc.) behind a consistent interface. This simplifies connecting to different services without learning each service's specific authentication patterns.

### Credential Reuse

The same service connector can be reused across multiple stack components, reducing credential duplication and making credential rotation easier:

```bash
# Register a connector once
zenml service-connector register my-aws-connector --type aws ...

# Use it with multiple components
zenml artifact-store register s3-store --type s3 --connector my-aws-connector ...
zenml container-registry register ecr-registry --type ecr --connector my-aws-connector ...
```

### Enhanced Security

Service connectors enforce the principle of least privilege by restricting access to only the resources needed for each operation. This limits exposure in case credentials are compromised.

### Resource Discovery

Service connectors can discover available resources, making it easier to configure stack components:

```bash
# List available resources through a connector
zenml service-connector list-resources my-aws-connector --resource-type s3-bucket
```

## Authentication Methods

Service connectors support multiple authentication methods for each service type. Common authentication methods include:

- **API keys and secrets**
- **OAuth tokens**
- **Client credentials (ID/secret pairs)**
- **Service accounts**
- **Managed identities (on cloud platforms)**
- **Temporary credentials and tokens**

## Working with Service Connectors

### Registering a Service Connector

You can register a service connector using the CLI:

```bash
zenml service-connector register CONNECTOR_NAME \
    --type CONNECTOR_TYPE \
    --auth-method AUTH_METHOD \
    [authentication-specific arguments...]
```

For example:

```bash
# Register an AWS connector using a credentials file
zenml service-connector register aws-dev \
    --type aws \
    --auth-method profile \
    --profile=dev-account
```

### Listing and Inspecting Connectors

```bash
# List all connectors
zenml service-connector list

# Get details about a specific connector
zenml service-connector describe CONNECTOR_NAME

# List resources available through a connector
zenml service-connector list-resources CONNECTOR_NAME
```

### Using Connectors with Stack Components

Service connectors can be attached to stack components either during registration or by updating existing components:

```bash
# During component registration
zenml artifact-store register s3-store \
    --type s3 \
    --bucket my-bucket \
    --connector aws-dev

# Update an existing component
zenml artifact-store update s3-store --connector aws-dev
```

## Service Connector Types

ZenML supports service connectors for various cloud providers and services, including:

- **AWS**: For Amazon Web Services (S3, ECR, etc.)
- **GCP**: For Google Cloud Platform (GCS, GCR, etc.)
- **Azure**: For Microsoft Azure (Blob Storage, ACR, etc.)
- **Kubernetes**: For Kubernetes clusters
- **Docker**: For Docker registries
- **GitHub**: For GitHub repositories
- **Generic** and **HTTP** for other services

Each connector type has specific resource types it can access and authentication methods it supports.

## Best Practices

- **Use descriptive names** for connectors that indicate their purpose or environment
- **Limit permissions** to only what's necessary for each connector
- **Rotate credentials** regularly for improved security
- **Use environment-specific connectors** for isolation between development and production
- **Document your connectors** for team collaboration

## Troubleshooting

Common issues with service connectors include:

- **Authentication failures**: Check that credentials are valid and have not expired
- **Permission errors**: Ensure the connector has the necessary permissions for the resources
- **Resource not found**: Verify that resource names/paths are correct and accessible
- **Connector type mismatch**: Confirm the connector type matches the resource type you're trying to access

Use the `verify` command to check if a connector is working correctly:

```bash
zenml service-connector verify CONNECTOR_NAME
```

## Next Steps

- Learn about [AWS integrations](aws.md)
- Explore [Azure integrations](azure.md) 
- Discover [GCP integrations](gcp.md)
- Understand how to [deploy your stack](deployment.md) across different environments 