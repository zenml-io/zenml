---
description: >-
  Managing authentication to cloud services and resources with Service
  Connectors
icon: link
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Service Connectors

Service Connectors provide a unified way to handle authentication between ZenML and external services like cloud providers. They are a critical part of working with cloud-based stacks and significantly simplify the authentication challenge in ML workflows.

A service connector is an entity that:

1. Stores credentials and authentication configuration
2. Provides secure access to specific resources
3. Can be shared across multiple stack components
4. Manages permissions and access scopes
5. Automatically generates and refreshes short-lived access tokens

Think of service connectors as secure bridges between your ZenML stack components and external services that abstract away the complexity of different authentication methods across cloud providers.

## Why Use Service Connectors?

### The Authentication Challenge

ML workflows typically interact with multiple cloud services (storage, compute, model registries, etc.), creating complex credential management challenges. Without service connectors, you would need to:

* Configure authentication separately for each stack component
* Handle different authentication methods for each cloud service
* Store and manage credentials manually in code or configuration files
* Update credentials in multiple places when they change
* Implement proper security practices across all credential usage
* Spend engineering time on authentication rather than ML development

<figure><img src="../../.gitbook/assets/ConnectorsDiagram.png" alt=""><figcaption><p>Service Connectors abstract away complexity and implement security best practices</p></figcaption></figure>

Service connectors solve these problems by providing a single point of authentication that can be reused across your stack components, decoupling credentials from code and configuration.

### Key Benefits

* **Centralized Authentication**: Manage all your cloud credentials in one place
* **Credential Reuse**: Configure authentication once, use it with multiple components
* **Security**: Implement security best practices with short-lived tokens, principle of least privilege, and reduced credential exposure
* **Authentication Abstraction**: Eliminate credential handling code in pipeline components while supporting multiple auth methods
* **Resource Discovery**: Easily find available resources on your cloud accounts
* **Simplified Rotation**: Update credentials in one place when they change
* **Team Sharing**: Securely share access to resources within your team
* **Multi-cloud Support**: Use the same interface across AWS, GCP, Azure and other services with consistent patterns

### Supported Cloud Providers and Services

ZenML supports connectors for major cloud providers and services:

* **AWS**: For Amazon Web Services (S3, ECR, SageMaker, etc.)
* **GCP**: For Google Cloud Platform (GCS, GCR, Vertex AI, etc.)
* **Azure**: For Microsoft Azure (Blob Storage, ACR, AzureML, etc.)
* **Kubernetes**: For Kubernetes clusters

Each connector type supports authentication methods specific to that service.

## Working with Service Connectors

### Creating and Managing Connectors

Service connectors can be created with different authentication methods
depending on your cloud provider and security requirements.

![Authentication with Service Connectors](../../.gitbook/assets/authentication_with_connectors.png)

Here is an example of how to register a new connector:

```bash
# Register a new connector using AWS profile
zenml service-connector register aws-dev \
    --type aws \
    --auth-method profile \
    --profile=dev-account

# GCP connector using service account
zenml service-connector register gcp-prod \
    --type gcp \
    --auth-method service-account \
    --service-account-json=/path/to/sa.json

# List all connectors
zenml service-connector list

# Verify a connector works
zenml service-connector verify aws-dev
```

The authentication happens transparently to your ML code. You don't need to handle credentials in your pipeline steps - the service connector takes care of that for you.

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
* **Create separate connectors** for development, staging, and production environments
* **Apply least privilege** when configuring connector permissions and resource scopes
* **Regularly rotate credentials** for enhanced security
* **Document your connector configurations** for team knowledge sharing
* **Leverage short-lived tokens** where possible instead of long-lived credentials
* **Avoid hard-coding credentials** in your code and config files, use service connectors instead

## Code Example

When using service connectors, your pipeline code remains clean and focused on ML logic:

```python
from zenml import step

# Without service connectors
@step
def upload_model(model):
    # Need to handle authentication manually
    import boto3
    session = boto3.Session(aws_access_key_id='AKIAXXXXXXXX',
                          aws_secret_access_key='SECRET')
    s3 = session.client('s3')
    s3.upload_file(model.path, 'my-bucket', 'models/model.pkl')

# With service connectors
@step
def upload_model_with_connector(model):
    # Authentication handled by the service connector
    # No credential handling required
    from zenml.integrations.s3.artifact_stores import S3ArtifactStore
    store = S3ArtifactStore()
    store.copyfile(model.path, 'models/model.pkl')
```

## Next Steps

* Learn how to [deploy stacks](https://docs.zenml.io/stacks/deployment) using service connectors
* Explore [authentication methods](https://docs.zenml.io/how-to/infrastructure-deployment/auth-management/service-connectors-guide) for different cloud providers 
* Understand how to [reference secrets in stack configuration](https://docs.zenml.io/how-to/infrastructure-deployment/stack-deployment/reference-secrets-in-stack-configuration)
* Read our [blog post](https://www.zenml.io/blog/how-to-simplify-authentication-in-machine-learning-pipelines-for-mlops) on how service connectors simplify authentication in ML pipelines
