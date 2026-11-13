"""Submit expanded registered model files without loading weights in the deployment step."""

from uuid import UUID

from zenml import pipeline, step
from zenml.artifacts.unmaterialized_artifact import UnmaterializedArtifact
from zenml.client import Client
from zenml.model_deployers.managed_model_deployer import ManagedModelDeployer
from zenml.models.managed_model import FullModelPackage, ModelArtifactReference


@step(enable_cache=False)
def deploy_registered_model(
    model: UnmaterializedArtifact,
    tokenizer: UnmaterializedArtifact,
    name: str,
    profile: str,
    request_key: str,
) -> str:
    """Accept a durable deployment using registered model and tokenizer references.

    Args:
        model: Expanded Transformers safetensors artifact.
        tokenizer: Expanded tokenizer artifact saved by the training workflow.
        name: Human-readable service name.
        profile: Operator-approved serving profile.
        request_key: Persisted caller intent key reused across retries.

    Returns:
        Stable service ID; acceptance does not imply inference readiness.

    Raises:
        ValueError: If the active stack does not use the managed deployer.
    """
    deployer = Client().active_stack.model_deployer
    if not isinstance(deployer, ManagedModelDeployer):
        raise ValueError(
            "Register and select the managed model-deployer flavor."
        )
    package = FullModelPackage(
        model=ModelArtifactReference(artifact_version_id=model.id),
        tokenizer=ModelArtifactReference(artifact_version_id=tokenizer.id),
    )
    service = deployer.deploy_package(
        package, name=name, serving_profile=profile, request_key=request_key
    )
    return str(service.id)


@pipeline
def serve_registered_model(
    model_artifact_id: UUID,
    tokenizer_artifact_id: UUID,
    name: str,
    profile: str,
    request_key: str,
) -> None:
    """Submit existing model artifacts through the same API used by bots and SDK clients.

    Args:
        model_artifact_id: Registered expanded model export.
        tokenizer_artifact_id: Registered matching tokenizer export.
        name: Human-readable service name.
        profile: Operator-approved serving profile.
        request_key: Persisted intent key reused for an identical retry.
    """
    client = Client()
    deploy_registered_model(
        model=client.get_artifact_version(model_artifact_id),
        tokenizer=client.get_artifact_version(tokenizer_artifact_id),
        name=name,
        profile=profile,
        request_key=request_key,
    )
