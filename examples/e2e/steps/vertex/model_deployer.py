from typing_extensions import Annotated

from zenml import ArtifactConfig, get_step_context, step
from zenml.client import Client
from zenml.integrations.gcp.services.vertex_deployment import (
    VertexDeploymentConfig,
    VertexDeploymentService,
)
from zenml.logger import get_logger

logger = get_logger(__name__)


@step(enable_cache=False)
def model_deployer(
    model_registry_uri: str,
    name: str = "e2e_use_case",
) -> Annotated[
    VertexDeploymentService,
    ArtifactConfig(name="vertex_deployment", is_deployment_artifact=True),
]:
    """Model deployer step.

    Args:
        model_registry_uri: URI of the model in the model registry.
        is_promoted: Whether the model was promoted to production.

    Returns:
        The deployed model service.
    """
    zenml_client = Client()
    current_model = get_step_context().model
    model_deployer = zenml_client.active_stack.model_deployer
    # Create deployment configuration with proper model name and version
    vertex_deployment_config = VertexDeploymentConfig(
        location="europe-west1",
        name="e2e_use_case",
        display_name="zenml-vertex-quickstart",
        model_name=model_registry_uri,  # This is the full resource name from registration
        model_version=current_model.version,  # Specify the version explicitly
        description="An example of deploying a model using the Vertex AI Model Deployer",
        sync=True,  # Wait for deployment to complete
        traffic_percentage=100,  # Route all traffic to this version
    )
    service = model_deployer.deploy_model(
        config=vertex_deployment_config,
        service_type=VertexDeploymentService.SERVICE_TYPE,
    )

    logger.info(
        f"The deployed service info: {model_deployer.get_model_server_info(service)}"
    )
    return service
