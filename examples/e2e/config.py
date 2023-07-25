from pydantic import BaseConfig

from zenml.config import DockerSettings
from zenml.integrations.constants import (
    AWS,
    EVIDENTLY,
    KUBEFLOW,
    KUBERNETES,
    MLFLOW,
    SKLEARN,
    SLACK,
)
from zenml.model_registries.base_model_registry import ModelVersionStage

NOTIFY_ON_SUCCESS = False
NOTIFY_ON_FAILURE = False


class MetaConfig(BaseConfig):
    pipeline_name_training = "e2e_example_training"
    pipeline_name_batch_inference = "e2e_example_batch_inference"
    mlflow_model_name = "e2e_example_model"
    target_env = ModelVersionStage.STAGING


DOCKER_SETTINGS = DockerSettings(
    required_integrations=[
        AWS,
        EVIDENTLY,
        KUBEFLOW,
        KUBERNETES,
        MLFLOW,
        SKLEARN,
        SLACK,
    ],
)
