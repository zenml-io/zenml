# Vertex AI Model Deployer

[Vertex AI](https://cloud.google.com/vertex-ai) provides managed infrastructure for deploying machine learning models at scale. The Vertex AI Model Deployer in ZenML allows you to deploy models to Vertex AI endpoints, providing a scalable and fully managed solution for model serving.

## When to use it?

Use the Vertex AI Model Deployer when:

- You are leveraging Google Cloud Platform (GCP) and wish to integrate with its native ML serving infrastructure.
- You need enterprise-grade model serving capabilities complete with autoscaling and GPU acceleration.
- You require a fully managed solution that abstracts away the operational overhead of serving models.
- You need to deploy models directly from your Vertex AI Model Registry—or even from other registries or artifacts.
- You want seamless integration with GCP services like Cloud Logging, IAM, and VPC.

This deployer is especially useful for production deployments, high-availability serving, and dynamic scaling based on workloads.

{% hint style="info" %}
For best results, the Vertex AI Model Deployer works with a Vertex AI Model Registry in your ZenML stack. This allows you to register models with detailed metadata and configuration and then deploy a specific version seamlessly.
{% endhint %}

## How to deploy it?

The Vertex AI Model Deployer is enabled via the ZenML GCP integration. First, install the integration:

```shell
zenml integration install gcp -y
```

### Authentication and Service Connector Configuration

The deployer requires proper GCP authentication. The recommended approach is to use the ZenML Service Connector:

```shell
# Register the service connector with a service account key
zenml service-connector register vertex_deployer_connector \
    --type gcp \
    --auth-method=service-account \
    --project_id=<PROJECT_ID> \
    --service_account_json=@vertex-deployer-sa.json \
    --resource-type gcp-generic

# Register the model deployer and connect it to the service connector
zenml model-deployer register vertex_deployer \
    --flavor=vertex \
    --location=us-central1 \
    --connector vertex_deployer_connector
```

{% hint style="info" %}
The service account used for deployment must have the following permissions:
- `Vertex AI User` to enable model deployments
- `Vertex AI Service Agent` for model endpoint management
- `Storage Object Viewer` if the model artifacts reside in Google Cloud Storage
{% endhint %}

## How to use it

A complete usage example is available in the [ZenML Examples repository](https://github.com/zenml-io/zenml-projects/tree/main/vertex-registry-and-deployer).

### Deploying a Model in a Pipeline

Below is an example of a deployment step that uses the updated configuration options. In this example, the deployment configuration supports:

- **Model versioning**: Explicitly provide the model version (using the full resource name from the model registry).
- **Display name and Sync mode**: Fields such as `display_name` (for a friendly endpoint name) and `sync` (to wait for deployment completion) are now available.
- **Traffic configuration**: Route a certain percentage (e.g., 100%) of traffic to this deployment.
- **Advanced options**: You can still specify custom container settings, resource specifications (including GPU options), and explanation configuration via shared classes from `vertex_base_config.py`.

```python
from typing_extensions import Annotated
from zenml import ArtifactConfig, get_step_context, step
from zenml.client import Client
from zenml.integrations.gcp.services.vertex_deployment import (
    VertexDeploymentConfig,
    VertexDeploymentService,
)

@step(enable_cache=False)
def model_deployer(
    model_registry_uri: str,
    is_promoted: bool = False,
) -> Annotated[
    VertexDeploymentService,
    ArtifactConfig(name="vertex_deployment", is_deployment_artifact=True),
]:
    """Model deployer step.

    Args:
        model_registry_uri: The full resource name of the model in the registry.
        is_promoted: Flag indicating if the model is promoted to production.

    Returns:
        The deployed model service.
    """
    if not is_promoted:
        # Skip deployment if the model is not promoted.
        return None
    else:
        zenml_client = Client()
        current_model = get_step_context().model
        model_deployer = zenml_client.active_stack.model_deployer

        # Create deployment configuration with advanced options.
        vertex_deployment_config = VertexDeploymentConfig(
            location="europe-west1",
            name=current_model.name,  # Unique endpoint name in Vertex AI.
            display_name="zenml-vertex-quickstart",
            model_name=model_registry_uri,  # Fully qualified model name (from model registry).
            model_version=current_model.version,  # Specify the model version explicitly.
            description="An example of deploying a model using the Vertex AI Model Deployer",
            sync=True,  # Wait for deployment to complete before proceeding.
            traffic_percentage=100,  # Route 100% of traffic to this model version.
            # (Optional) Advanced configurations:
            # container=VertexAIContainerSpec(
            #     image_uri="your-custom-image:latest",
            #     ports=[8080],
            #     env={"ENV_VAR": "value"}
            # ),
            # resources=VertexAIResourceSpec(
            #     accelerator_type="NVIDIA_TESLA_T4",
            #     accelerator_count=1,
            #     machine_type="n1-standard-4",
            #     min_replica_count=1,
            #     max_replica_count=3,
            # ),
            # explanation=VertexAIExplanationSpec(
            #     metadata={"method": "integrated-gradients"},
            #     parameters={"num_integral_steps": 50}
            # )
        )

        service = model_deployer.deploy_model(
            config=vertex_deployment_config,
            service_type=VertexDeploymentService.SERVICE_TYPE,
        )

        return service
```

*Example: [`model_deployer.py`](../../examples/vertex-registry-and-deployer/steps/model_deployer.py)*

### Configuration Options

The Vertex AI Model Deployer leverages a comprehensive configuration system defined in the shared base configuration and deployer-specific settings:

- **Basic Settings:**
  - `location`: The GCP region for deployment (e.g., "us-central1" or "europe-west1").
  - `name`: Unique identifier for the deployed endpoint.
  - `display_name`: A human-friendly name for the endpoint.
  - `model_name`: The fully qualified model name from the model registry.
  - `model_version`: The version of the model to deploy.
  - `description`: A textual description of the deployment.
  - `sync`: A flag to indicate whether the deployment should wait until completion.
  - `traffic_percentage`: The percentage of incoming traffic to route to this deployment.

- **Container and Resource Configuration:**
  - Configurations provided via [VertexAIContainerSpec](../../integrations/gcp/flavors/vertex_base_config.py) allow you to specify a custom serving container image, HTTP routes (`predict_route`, `health_route`), environment variables, and port exposure.
  - [VertexAIResourceSpec](../../integrations/gcp/flavors/vertex_base_config.py) lets you override the default machine type, number of replicas, and even GPU options.

- **Advanced Settings:**
  - Service account, network configuration, and customer-managed encryption keys.
  - Model explanation settings via `VertexAIExplanationSpec` if you need integrated model interpretability.

These options are defined across the [Vertex AI Base Config](../../integrations/gcp/flavors/vertex_base_config.py) and the deployer–specific configuration in [VertexModelDeployerFlavor](../../integrations/gcp/flavors/vertex_model_deployer_flavor.py).

### Limitations and Considerations

1. **Stack Requirements:**
   - It is recommended to pair the deployer with a Vertex AI Model Registry in your stack.
   - Compatible with both local and remote orchestrators.
   - Requires valid GCP credentials and permissions.

2. **Authentication:**
   - Best practice is to use service connectors for secure and managed authentication.
   - Supports multiple authentication methods (service accounts, local credentials).

3. **Costs:**
   - Vertex AI endpoints will incur costs based on machine type and uptime.
   - Utilize autoscaling (via configured `min_replica_count` and `max_replica_count`) to manage cost.

4. **Region Consistency:**
   - Ensure that the model and deployment are created in the same GCP region.

For more details, please refer to the [SDK docs](https://sdkdocs.zenml.io) and the relevant implementation files:
- [`vertex_model_deployer.py`](../../integrations/gcp/model_deployers/vertex_model_deployer.py)
- [`vertex_base_config.py`](../../integrations/gcp/flavors/vertex_base_config.py)
- [`vertex_model_deployer_flavor.py`](../../integrations/gcp/flavors/vertex_model_deployer_flavor.py)