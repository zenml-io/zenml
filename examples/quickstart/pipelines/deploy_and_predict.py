from steps.model_deployer import model_deployer
from steps.prediction_service_loader import prediction_service_loader
from steps.predictor import predictor
from steps.training_data_loader import training_data_loader

from zenml import pipeline


@pipeline
def deploy_and_predict() -> None:
    """Deploy the best model and run some predictions."""
    prediction_service_loader.after(model_deployer)

    model_deployer()
    _, inference_data, _, _ = training_data_loader()
    model_deployment_service = prediction_service_loader()
    predictor(service=model_deployment_service, data=inference_data)
