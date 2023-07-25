from pydantic import BaseConfig

from zenml.model_registries.base_model_registry import ModelVersionStage

NOTIFY_ON_SUCCESS = False
NOTIFY_ON_FAILURE = False


class MetaConfig(BaseConfig):
    pipeline_name = "e2e_example_pipeline"
    mlflow_model_name = "e2e_example_model"
    runs_prefix = "e2e_example_run_"
    preprocess_pipeline_artifact_name = "preprocess_pipeline"
    target_env = ModelVersionStage.STAGING
