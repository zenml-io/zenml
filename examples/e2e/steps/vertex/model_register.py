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
    name: str = "e2e_use_case",
) -> Annotated[str, ArtifactConfig(name="model_registry_uri")]:
    """Model registration step.

    Registers a model version in the Vertex AI Model Registry with extended configuration
    and returns the model's source URI. This configuration embeds details such as container,
    resource, explanation settings etc. so that the deployment can reuse these pre-configured
    settings from the registry.
    """
    if is_promoted:
        # Get the current model from the step context
        current_model = get_step_context().model

        client = Client()
        model_registry = client.active_stack.model_registry
        # Create an extended model configuration using the base settings for Vertex AI
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
            model_source_uri=current_model.get_model_artifact("model").uri,
            description="ZenML model version registered with extended configuration",
            metadata=ModelRegistryModelMetadata(
                zenml_pipeline_name=get_step_context().pipeline.name,
                zenml_pipeline_run_uuid=str(
                    get_step_context().pipeline_run.id
                ),
                zenml_step_name=get_step_context().step_run.name,
            ),
            config=model_config,
        )
        logger.info(
            f"Model version {model_version.version} registered in Model Registry"
        )

        # Return the full resource name of the registered model
        return model_version.metadata.resource_name
    else:
        return ""
