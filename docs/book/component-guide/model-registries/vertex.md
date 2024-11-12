# Vertex AI Model Registry

[Vertex AI](https://cloud.google.com/vertex-ai) is Google Cloud's unified ML platform that helps you build, deploy, and scale ML models. The Vertex AI Model Registry is a centralized repository for managing your ML models throughout their lifecycle. ZenML's Vertex AI Model Registry integration allows you to register, version, and manage your models using Vertex AI's infrastructure.

## When would you want to use it?

You should consider using the Vertex AI Model Registry when:

* You're already using Google Cloud Platform (GCP) and want to leverage its native ML infrastructure
* You need enterprise-grade model management capabilities with fine-grained access control
* You want to track model lineage and metadata in a centralized location
* You're building ML pipelines that need to integrate with other Vertex AI services
* You need to manage model deployment across different GCP environments

This is particularly useful in the following scenarios:

* Building production ML pipelines that need to integrate with GCP services
* Managing multiple versions of models across development and production environments
* Tracking model artifacts and metadata in a centralized location
* Deploying models to Vertex AI endpoints for serving

{% hint style="warning" %}
Important: The Vertex AI Model Registry implementation only supports the model version interface, not the model interface. This means you cannot register, delete, or update models directly - you can only work with model versions. Operations like `register_model()`, `delete_model()`, and `update_model()` are not supported.

Unlike platforms like MLflow where you first create a model container and then add versions to it, Vertex AI combines model registration and versioning into a single operation:

- When you upload a model, it automatically creates both the model and its first version
- Each subsequent upload with the same display name creates a new version
- You cannot create an empty model container without a version
{% endhint %}

## How do you deploy it?

The Vertex AI Model Registry flavor is provided by the GCP ZenML integration. First, install the integration:

```shell
zenml integration install gcp -y
```

### Authentication and Service Connector Configuration

The Vertex AI Model Registry requires proper GCP authentication. The recommended way to configure this is using the ZenML Service Connector functionality. You have several options for authentication:

1. Using a GCP Service Connector with a dedicated service account (Recommended):
```shell
# Register the service connector with a service account key
zenml service-connector register vertex_registry_connector \
    --type gcp \
    --auth-method=service-account \
    --project_id=<PROJECT_ID> \
    --service_account_json=@vertex-registry-sa.json \
    --resource-type gcp-generic

# Register the model registry
zenml model-registry register vertex_registry \
    --flavor=vertex \
    --location=us-central1

# Connect the model registry to the service connector
zenml model-registry connect vertex_registry --connector vertex_registry_connector
```

2. Using local gcloud credentials:
```shell
# Register the model registry using local gcloud auth
zenml model-registry register vertex_registry \
    --flavor=vertex \
    --location=us-central1
```

{% hint style="info" %}
The service account used needs the following permissions:
- `Vertex AI User` role for creating and managing model versions
- `Storage Object Viewer` role if accessing models stored in Google Cloud Storage
{% endhint %}

## How do you use it?

### Register models inside a pipeline

Here's an example of how to use the Vertex AI Model Registry in your ZenML pipeline using the provided model registration step:

```python
from typing_extensions import Annotated
from zenml import ArtifactConfig, get_step_context, step
from zenml.client import Client
from zenml.logger import get_logger

logger = get_logger(__name__)

@step(enable_cache=False)
def model_register() -> Annotated[str, ArtifactConfig(name="model_registry_uri")]:
    """Model registration step."""
    # Get the current model from the context
    current_model = get_step_context().model

    client = Client()
    model_registry = client.active_stack.model_registry
    model_version = model_registry.register_model_version(
        name=current_model.name,
        version=str(current_model.version),
        model_source_uri=current_model.get_model_artifact("sklearn_classifier").uri,
        description="ZenML model registered after promotion",
    )
    logger.info(
        f"Model version {model_version.version} registered in Model Registry"
    )
    
    return model_version.model_source_uri
```

### Configuration Options

The Vertex AI Model Registry accepts the following configuration options:

* `location`: The GCP region where the model registry will be created (e.g., "us-central1")
* `project_id`: (Optional) The GCP project ID. If not specified, will use the default project
* `credentials`: (Optional) GCP credentials configuration

### Working with Model Versions

Since the Vertex AI Model Registry only supports version-level operations, here's how to work with model versions:

```shell
# List all model versions
zenml model-registry models list-versions <model-name>

# Get details of a specific model version
zenml model-registry models get-version <model-name> -v <version>

# Delete a model version
zenml model-registry models delete-version <model-name> -v <version>
```

### Key Differences from MLflow Model Registry

Unlike the MLflow Model Registry, the Vertex AI implementation has some important differences:

1. **Version-Only Interface**: Vertex AI only supports model version operations. You cannot register, delete, or update models directly - only their versions.
2. **Authentication**: Uses GCP service connectors for authentication, similar to other Vertex AI services in ZenML.
3. **Staging Levels**: Vertex AI doesn't have built-in staging levels (like Production, Staging, etc.) - these are handled through metadata.
4. **Default Container Images**: Vertex AI requires a serving container image URI, which defaults to the scikit-learn prediction container if not specified.
5. **Managed Service**: As a fully managed service, you don't need to worry about infrastructure management, but you need valid GCP credentials.

### Limitations

Based on the implementation, there are some limitations to be aware of:

1. The `register_model()`, `update_model()`, and `delete_model()` methods are not implemented as Vertex AI only supports registering model versions
3. It's preferable for the models to be given a serving container image URI specified to avoid using the default scikit-learn prediction container and to ensure compatibility with Vertex AI endpoints
when deploying models.
4. All registered models by the integration are automatically labeled with `managed_by="zenml"` for tracking purposes

Check out the [SDK docs](https://sdkdocs.zenml.io/latest/integration\_code\_docs/integrations-gcp/#zenml.integrations.gcp.model\_registry) to see more about the interface and implementation.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>