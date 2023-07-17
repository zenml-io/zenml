from steps.register_model import model_name
from zenml.client import Client
from zenml.integrations.mlflow.steps.mlflow_deployer import (
    mlflow_model_registry_deployer_step,
)

most_recent_model_version_number = int(
    Client()
    .active_stack.model_registry.list_model_versions(metadata={})[0]
    .version
)

model_deployer = mlflow_model_registry_deployer_step.with_options(
    parameters=dict(
        registry_model_name=model_name,
        registry_model_version=most_recent_model_version_number,
    )
)
