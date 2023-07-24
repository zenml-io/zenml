from steps.register_model import model_name
from zenml.integrations.mlflow.steps.mlflow_deployer import (
    mlflow_model_registry_deployer_step,
)

model_deployer = mlflow_model_registry_deployer_step.with_options(
    parameters=dict(
        registry_model_name=model_name,
        registry_model_version=1,
        timeout=300,
    )
)
