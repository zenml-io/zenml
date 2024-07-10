from steps import get_historical_features, feature_printer

from zenml.config import DockerSettings
from zenml.integrations.constants import FEAST
from zenml import pipeline
from zenml.logger import get_logger
from zenml.client import Client

from rich import print

logger = get_logger(__name__)

docker_settings = DockerSettings(required_integrations=[FEAST])


@pipeline(enable_cache=False, settings={"docker": docker_settings})
def feast_pipeline():
    """Links all the steps together in a pipeline."""
    features = get_historical_features()
    feature_printer(features)




if __name__ == "__main__":
    feast_pipeline()

    zc = Client()
    last_run = zc.get_pipeline("feast_pipeline").last_successful_run

    historical_features_step = last_run.steps['feature_printer']
    print("HISTORICAL FEATURES:")
    print(historical_features_step.output.load())
