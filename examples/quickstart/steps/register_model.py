from zenml.integrations.mlflow.steps.mlflow_registry import (
    mlflow_register_model_step,
)

model_name = "zenml-quickstart-model"

register_model = mlflow_register_model_step.with_options(
    parameters=dict(
        name=model_name,
        description="The first run of the Quickstart pipeline.",
    )
)
