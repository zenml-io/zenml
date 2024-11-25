# 


from zenml.client import Client
from zenml.logger import get_logger
from zenml.model_registries.base_model_registry import ModelVersionStage

logger = get_logger(__name__)


def promote_in_model_registry(
    latest_version: str, current_version: str, model_name: str, target_env: str
):
    """Promote model version in model registry to a given stage.

    Args:
        latest_version: version to be promoted
        current_version: currently promoted version
        model_name: name of the model in registry
        target_env: stage for promotion
    """
    model_registry = Client().active_stack.model_registry
    model_registry.configure_mlflow()
    if latest_version != current_version:
        model_registry.update_model_version(
            name=model_name,
            version=current_version,
            stage=ModelVersionStage(ModelVersionStage.ARCHIVED),
            metadata={},
        )
    model_registry.update_model_version(
        name=model_name,
        version=latest_version,
        stage=ModelVersionStage(target_env),
        metadata={},
    )
