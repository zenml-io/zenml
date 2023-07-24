from steps.model_deployer import model_deployer
from steps.prediction_service_loader import prediction_service_loader
from steps.predictor import predictor
from steps.training_data_loader import training_data_loader

from zenml import pipeline
from zenml.config import DockerSettings
from zenml.integrations.constants import MLFLOW, SKLEARN

docker_settings = DockerSettings(
    required_integrations=[MLFLOW, SKLEARN],
    requirements=[
        "numpy==1.24.3",
        "scipy==1.10.1",
        "typing-extensions==4.6.3",
    ],
)


@pipeline(enable_cache=True, settings={"docker": docker_settings})
def deploy_and_predict() -> None:
    """Deploy the best model and run some predictions."""
    prediction_service_loader.after(model_deployer)

    model_deployer()
    _, inference_data, _, _ = training_data_loader()
    model_deployment_service = prediction_service_loader()
    predictor(service=model_deployment_service, data=inference_data)
