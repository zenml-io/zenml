from zenml import step
from zenml.client import Client
from zenml.services import BaseService


@step(enable_cache=False)
def prediction_service_loader() -> BaseService:
    """Load the model service of our train_and_register_model_pipeline."""
    client = Client()
    model_deployer = client.active_stack.model_deployer
    services = model_deployer.find_model_server(
        pipeline_name="train_and_register_model_pipeline",
    )
    return services[0]
