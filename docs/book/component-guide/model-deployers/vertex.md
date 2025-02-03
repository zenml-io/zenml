# Vertex AI Model Deployer

[Vertex AI](https://cloud.google.com/vertex-ai) provides managed infrastructure for deploying machine learning models at scale. The Vertex AI Model Deployer in ZenML allows you to deploy models to Vertex AI endpoints, providing a scalable and managed solution for model serving.

## When to use it?

You should use the Vertex AI Model Deployer when:

* You're already using Google Cloud Platform (GCP) and want to leverage its native ML infrastructure
* You need enterprise-grade model serving capabilities with autoscaling
* You want a fully managed solution for hosting ML models
* You need to handle high-throughput prediction requests
* You want to deploy models with GPU acceleration
* You need to monitor and track your model deployments
* You want to integrate with other GCP services like Cloud Logging, IAM, and VPC

This is particularly useful in the following scenarios:
* Deploying models to production with high availability requirements
* Serving models that need GPU acceleration
* Handling varying prediction workloads with autoscaling
* Building end-to-end ML pipelines on GCP

{% hint style="info" %}
The Vertex AI Model Deployer works best with a Vertex AI Model Registry in your stack, as this enables seamless model versioning and deployment. However, it can also work with other model registries or directly with model artifacts.

The deployer can be used with both local and remote orchestrators, making it flexible for different development and production scenarios.
{% endhint %}

## How to deploy it?

The Vertex AI Model Deployer is provided by the GCP ZenML integration. First, install the integration:

```shell
zenml integration install gcp -y
```

### Authentication and Service Connector Configuration

The Vertex AI Model Deployer requires proper GCP authentication. The recommended way to configure this is using the ZenML Service Connector functionality:

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
The service account needs the following permissions:
- `Vertex AI User` role for deploying models
- `Vertex AI Service Agent` role for managing model endpoints
- `Storage Object Viewer` role if accessing models stored in Google Cloud Storage
{% endhint %}

## How to use it

A full project example is available in the [ZenML Examples repository](https://github.com/zenml-io/zenml-projects/tree/main/vertex-registry-and-deployer).

### Deploy a model in a pipeline

Here's an example of how to use the Vertex AI Model Deployer in a ZenML pipeline:

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
) -> Annotated[
    VertexDeploymentService, 
    ArtifactConfig(name="vertex_deployment", is_deployment_artifact=True)
]:
    """Model deployer step."""
    zenml_client = Client()
    current_model = get_step_context().model
    model_registry_uri = current_model.get_model_artifact("model").uri
    model_deployer = zenml_client.active_stack.model_deployer

    # Configure the deployment
    vertex_deployment_config = VertexDeploymentConfig(
        location="europe-west1",
        name="zenml-vertex-quickstart",
        model_name=current_model.name,
        description="Vertex AI model deployment example",
        model_id=model_registry_uri,
        machine_type="n1-standard-4",
        min_replica_count=1,
        max_replica_count=3,
        # Optional advanced settings
        container=VertexAIContainerSpec(
            image_uri="your-custom-image:latest",
            ports=[8080],
            env={"ENV_VAR": "value"}
        ),
        resources=VertexAIResourceSpec(
            accelerator_type="NVIDIA_TESLA_T4",
            accelerator_count=1
        ),
        explanation=VertexAIExplanationSpec(
            metadata={"method": "integrated-gradients"},
            parameters={"num_integral_steps": 50}
        )
    )
    
    # Deploy the model
    service = model_deployer.deploy_model(
        config=vertex_deployment_config,
        service_type=VertexDeploymentService.SERVICE_TYPE,
    )
    
    return service
```

### Configuration Options

The Vertex AI Model Deployer uses a comprehensive configuration system that includes:

* Basic Configuration:
  * `location`: GCP region for deployment (e.g., "us-central1")
  * `name`: Name for the deployment endpoint
  * `model_name`: Name of the model being deployed
  * `model_id`: Model ID from the Vertex AI Model Registry

* Container Configuration (`VertexAIContainerSpec`):
  * `image_uri`: Custom serving container image
  * `ports`: Container ports to expose
  * `env`: Environment variables
  * `predict_route`: Custom prediction HTTP path
  * `health_route`: Custom health check path

* Resource Configuration (`VertexAIResourceSpec`):
  * `machine_type`: Type of machine to use (e.g., "n1-standard-4")
  * `accelerator_type`: GPU accelerator type
  * `accelerator_count`: Number of GPUs per replica
  * `min_replica_count`: Minimum number of serving replicas
  * `max_replica_count`: Maximum number of serving replicas

* Advanced Configuration:
  * `service_account`: Custom service account for the deployment
  * `network`: VPC network configuration
  * `encryption_spec_key_name`: Customer-managed encryption key
  * `enable_access_logging`: Enable detailed access logging
  * `explanation`: Model explanation configuration
  * `labels`: Custom resource labels

### Running Predictions

Once a model is deployed, you can run predictions using the service:

```python
from zenml.integrations.gcp.model_deployers import VertexModelDeployer
from zenml.services import ServiceState

# Get the deployed service
model_deployer = VertexModelDeployer.get_active_model_deployer()
services = model_deployer.find_model_server(
    pipeline_name="deployment_pipeline",
    pipeline_step_name="model_deployer",
    model_name="my_model",
)

if services:
    service = services[0]
    if service.is_running:
        # Run prediction
        prediction = service.predict(
            instances=[{"feature1": 1.0, "feature2": 2.0}]
        )
        print(f"Prediction: {prediction}")
```

### Limitations and Considerations

1. **Stack Requirements**: 
   - Works best with a Vertex AI Model Registry but can function without it
   - Compatible with both local and remote orchestrators
   - Requires valid GCP credentials and permissions

2. **Authentication**: 
   - Requires proper GCP credentials with Vertex AI permissions
   - Best practice is to use service connectors for authentication
   - Supports multiple authentication methods (service account, user account, workload identity)

3. **Costs**: 
   - Vertex AI endpoints incur costs based on machine type and uptime
   - Consider using autoscaling to optimize costs
   - Monitor usage through GCP Cloud Monitoring

4. **Region Availability**:
   - Service availability depends on Vertex AI regional availability
   - Model and endpoint must be in the same region
   - Consider data residency requirements when choosing regions

Check out the [SDK docs](https://sdkdocs.zenml.io) for more detailed information about the implementation.