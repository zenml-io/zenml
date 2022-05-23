import numpy as np

from zenml.repository import Repository
from zenml.services import BaseService
from zenml.steps import Output, step


@step(enable_cache=False)
def prediction_service_loader() -> BaseService:
    """Load the model service of our train_evaluate_deploy_pipeline."""
    repo = Repository(skip_repository_check=True)
    model_deployer = repo.active_stack.model_deployer
    services = model_deployer.find_model_server(
        pipeline_name="training_pipeline",
        pipeline_step_name="mlflow_model_deployer_step",
        running=True,
    )
    service = services[0]
    return service


@step
def predictor(
    service: BaseService,
    data: np.ndarray,
) -> Output(predictions=list):
    """Run a inference request against a prediction service"""
    service.start(timeout=10)  # should be a NOP if already started
    prediction = service.predict(data)
    prediction = prediction.argmax(axis=-1)
    print(f"Prediction is: {[prediction.tolist()]}")
    return [prediction.tolist()]
