from steps.best_model_selector import best_model_selector
from steps.register_model import register_model
from steps.trainers import random_forest_trainer_mlflow, sgd_trainer_mlflow
from steps.training_data_loader import training_data_loader

from zenml import pipeline
from zenml.config import DockerSettings
from zenml.integrations.constants import MLFLOW, SKLEARN

docker_settings = DockerSettings(required_integrations=[MLFLOW, SKLEARN])


@pipeline(enable_cache=True, settings={"docker": docker_settings})
def train_and_register_model_pipeline() -> None:
    """Train a model."""
    X_train, X_test, y_train, y_test = training_data_loader()
    model1 = random_forest_trainer_mlflow(X_train=X_train, y_train=y_train)
    model2 = sgd_trainer_mlflow(X_train=X_train, y_train=y_train)
    best_model, _ = best_model_selector(
        X_test=X_test, y_test=y_test, model1=model1, model2=model2
    )
    register_model(best_model)
