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

This is particularly useful in the following scenarios:
* Deploying models to production with high availability requirements
* Serving models that need GPU acceleration
* Handling varying prediction workloads with autoscaling
* Integrating model serving with other GCP services

{% hint style="warning" %}
The Vertex AI Model Deployer requires a Vertex AI Model Registry to be present in your stack. Make sure you have configured both components properly.
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

# Register the model deployer
zenml model-deployer register vertex_deployer \
    --flavor=vertex \
    --location=us-central1

# Connect the model deployer to the service connector
zenml model-deployer connect vertex_deployer --connector vertex_deployer_connector
```

{% hint style="info" %}
The service account needs the following permissions:
- `Vertex AI User` role for deploying models
- `Vertex AI Service Agent` role for managing model endpoints
{% endhint %}

## How to use it

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
    model_registry_uri: str,
) -> Annotated[
    VertexDeploymentService, 
    ArtifactConfig(name="vertex_deployment", is_deployment_artifact=True)
]:
    """Model deployer step."""
    zenml_client = Client()
    current_model = get_step_context().model
    model_deployer = zenml_client.active_stack.model_deployer

    # Configure the deployment
    vertex_deployment_config = VertexDeploymentConfig(
        location="europe-west1",
        name="zenml-vertex-quickstart",
        model_name=current_model.name,
        description="Vertex AI model deployment example",
        model_id=model_registry_uri,
        machine_type="n1-standard-4",  # Optional: specify machine type
        min_replica_count=1,  # Optional: minimum number of replicas
        max_replica_count=3,  # Optional: maximum number of replicas
    )
    
    # Deploy the model
    service = model_deployer.deploy_model(
        config=vertex_deployment_config,
        service_type=VertexDeploymentService.SERVICE_TYPE,
    )
    
    return service
```

### Configuration Options

The Vertex AI Model Deployer accepts a rich set of configuration options through `VertexDeploymentConfig`:

* Basic Configuration:
  * `location`: GCP region for deployment (e.g., "us-central1")
  * `name`: Name for the deployment endpoint
  * `model_name`: Name of the model being deployed
  * `model_id`: Model ID from the Vertex AI Model Registry

* Infrastructure Configuration:
  * `machine_type`: Type of machine to use (e.g., "n1-standard-4")
  * `accelerator_type`: GPU accelerator type if needed
  * `accelerator_count`: Number of GPUs per replica
  * `min_replica_count`: Minimum number of serving replicas
  * `max_replica_count`: Maximum number of serving replicas

* Advanced Configuration:
  * `service_account`: Custom service account for the deployment
  * `network`: VPC network configuration
  * `encryption_spec_key_name`: Customer-managed encryption key
  * `enable_access_logging`: Enable detailed access logging
  * `explanation_metadata`: Model explanation configuration
  * `autoscaling_target_cpu_utilization`: Target CPU utilization for autoscaling

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
   - Requires a Vertex AI Model Registry in the stack
   - All stack components must be non-local

2. **Authentication**: 
   - Requires proper GCP credentials with Vertex AI permissions
   - Best practice is to use service connectors for authentication

3. **Costs**: 
   - Vertex AI endpoints incur costs based on machine type and uptime
   - Consider using autoscaling to optimize costs

4. **Region Availability**:
   - Service availability depends on Vertex AI regional availability
   - Model and endpoint must be in the same region

Check out the [SDK docs](https://sdkdocs.zenml.io) for more detailed information about the implementation.