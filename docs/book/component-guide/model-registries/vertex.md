# Vertex AI Model Registry

[Vertex AI](https://cloud.google.com/vertex-ai) is Google Cloud's unified ML platform that helps you build, deploy, and scale ML models. The Vertex AI Model Registry is a centralized repository for managing your ML models throughout their lifecycle. With ZenML's Vertex AI Model Registry integration, you can register model versions—with extended configuration options—track metadata, and seamlessly deploy your models using Vertex AI's managed infrastructure.

## When would you want to use it?

You should consider using the Vertex AI Model Registry when:

- You're already using Google Cloud Platform (GCP) and want to leverage its native ML infrastructure.
- You need enterprise-grade model management with fine-grained access control.
- You want to track model lineage and metadata in a centralized location.
- You're building ML pipelines that integrate with other Vertex AI services.
- You need to deploy models with custom configurations such as defined container images, resource specifications, and additional metadata.

This registry is particularly useful in scenarios where you:
- Build production ML pipelines that require deployment to Vertex AI endpoints.
- Manage multiple versions of models across development, staging, and production.
- Need to register model versions with detailed configuration for robust deployment.

{% hint style="warning" %}
**Important:** The Vertex AI Model Registry implementation only supports the model **version** interface—not the model interface. This means that you cannot directly register, update, or delete models; you only have operations for model versions. A model container is automatically created with the first version, and subsequent uploads with the same display name create new versions.
{% endhint %}

## How do you deploy it?

The Vertex AI Model Registry flavor is enabled through the ZenML GCP integration. First, install the integration:

```shell
zenml integration install gcp -y
```

### Authentication and Service Connector Configuration

Vertex AI requires proper GCP authentication. The recommended configuration is via the ZenML Service Connector, which supports both service-account-based authentication and local gcloud credentials.

1. **Using a GCP Service Connector with a service account (Recommended):**
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
2. **Using local gcloud credentials:**
    ```shell
    # Register the model registry using local gcloud auth
    zenml model-registry register vertex_registry \
        --flavor=vertex \
        --location=us-central1
    ```

{% hint style="info" %}
The service account needs the following permissions:
- `Vertex AI User` role for creating and managing model versions.
- `Storage Object Viewer` role if accessing models stored in Google Cloud Storage.
{% endhint %}

## How do you use it?

### Registering Models inside a Pipeline with Extended Configuration

The Vertex AI Model Registry supports extended configuration options via the `VertexAIModelConfig` class (defined in the [vertex_base_config.py](../../integrations/gcp/flavors/vertex_base_config.py) file). This means you can specify additional details for your deployments such as:

- **Container configuration**: Use the `VertexAIContainerSpec` to define a custom serving container (e.g., specifying the `image_uri`, `predict_route`, `health_route`, and exposed ports).
- **Resource configuration**: Use the `VertexAIResourceSpec` to specify compute resources like `machine_type`, `min_replica_count`, and `max_replica_count`.
- **Additional metadata and labels**: Annotate your model registrations with pipeline details, stage information, and custom labels.

Below is an example of how you might register a model version in your ZenML pipeline:

```python
from typing_extensions import Annotated

from zenml import ArtifactConfig, get_step_context, step
from zenml.client import Client
from zenml.integrations.gcp.flavors.vertex_base_config import (
    VertexAIContainerSpec,
    VertexAIModelConfig,
    VertexAIResourceSpec,
)
from zenml.logger import get_logger
from zenml.model_registries.base_model_registry import (
    ModelRegistryModelMetadata,
)

logger = get_logger(__name__)


@step(enable_cache=False)
def model_register(
    is_promoted: bool = False,
) -> Annotated[str, ArtifactConfig(name="model_registry_uri")]:
    """Model registration step.

    Registers a model version in the Vertex AI Model Registry with extended configuration
    and returns the full resource name of the registered model.

    Extended configuration includes settings for container, resources, and metadata which can then be reused in
    subsequent model deployments.
    """
    if is_promoted:
        # Get the current model from the step context
        current_model = get_step_context().model

        client = Client()
        model_registry = client.active_stack.model_registry
        # Create an extended model configuration using Vertex AI base settings
        model_config = VertexAIModelConfig(
            location="europe-west1",
            container=VertexAIContainerSpec(
                image_uri="europe-docker.pkg.dev/vertex-ai/prediction/sklearn-cpu.1-5:latest",
                predict_route="predict",
                health_route="health",
                ports=[8080],
            ),
            resources=VertexAIResourceSpec(
                machine_type="n1-standard-4",
                min_replica_count=1,
                max_replica_count=1,
            ),
            labels={"env": "production"},
            description="Extended model configuration for Vertex AI",
        )

        # Register the model version with the extended configuration as metadata
        model_version = model_registry.register_model_version(
            name=current_model.name,
            version=str(current_model.version),
            model_source_uri=current_model.get_model_artifact("sklearn_classifier").uri,
            description="ZenML model version registered with extended configuration",
            metadata=ModelRegistryModelMetadata(
                zenml_pipeline_name=get_step_context().pipeline.name,
                zenml_pipeline_run_uuid=str(get_step_context().pipeline_run.id),
                zenml_step_name=get_step_context().step_run.name,
            ),
            config=model_config,
        )
        logger.info(f"Model version {model_version.version} registered in Model Registry")

        # Return the full resource name of the registered model
        return model_version.registered_model.name
    else:
        return ""
```

*Example: [`model_register.py`](../../examples/vertex-registry-and-deployer/steps/model_register.py)*

### Working with Model Versions

Since the Vertex AI Model Registry supports only version-level operations, here are some commands to manage model versions:

```shell
# List all model versions
zenml model-registry models list-versions <model-name>

# Get details of a specific model version
zenml model-registry models get-version <model-name> -v <version>

# Delete a model version
zenml model-registry models delete-version <model-name> -v <version>
```

### Configuration Options

The Vertex AI Model Registry accepts several configuration options, now enriched with extended settings:

- **location**: The GCP region where your resources will be created (e.g., "us-central1" or "europe-west1").
- **project_id**: (Optional) A GCP project ID override.
- **credentials**: (Optional) GCP credentials configuration.
- **container**: (Optional) Detailed container settings (defined via `VertexAIContainerSpec`) for the model's serving container such as:
  - `image_uri`
  - `predict_route`
  - `health_route`
  - `ports`
- **resources**: (Optional) Compute resource settings (using `VertexAIResourceSpec`) like `machine_type`, `min_replica_count`, and `max_replica_count`.
- **labels** and **metadata**: Additional annotation data for organizing and tracking your model versions.

These configuration options are specified in the [Vertex AI Base Config](../../integrations/gcp/flavors/vertex_base_config.py) and further extended in the [Vertex AI Model Registry Flavor](../../integrations/gcp/flavors/vertex_model_registry_flavor.py).

### Key Differences from Other Model Registries

1. **Version-Only Interface**: Vertex AI only supports version-level operations for model registration.
2. **Authentication**: Uses GCP service connectors and local credentials integrated via ZenML.
3. **Extended Configuration**: Register model versions with detailed settings for container, resources, and metadata through `VertexAIModelConfig`.
4. **Managed Service**: As a fully managed service, Vertex AI handles infrastructure management while you focus on your ML models.

## Limitations

- The methods `register_model()`, `update_model()`, and `delete_model()` are not implemented; you can only work with model versions.
- It is recommended to specify a serving container image URI rather than rely on the default scikit-learn container to ensure compatibility with Vertex AI endpoints.
- All models registered through this integration are automatically labeled with `managed_by="zenml"` for consistent tracking.

For more detailed information, check out the [SDK docs](https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-gcp/#zenml.integrations.gcp.model_registry).

<figure>
  <img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf">
  <figcaption>ZenML in action</figcaption>
</figure>