from steps.best_model_selector import best_model_selector
from steps.register_model import register_model
from steps.trainers import random_forest_trainer_mlflow, sgd_trainer_mlflow
from steps.training_data_loader import training_data_loader

from zenml import pipeline


@pipeline(enable_cache=True)
def train_and_register_model_pipeline() -> None:
    """Train a model."""
    X_train, X_test, y_train, y_test = training_data_loader()
    model1 = random_forest_trainer_mlflow(X_train=X_train, y_train=y_train)
    model2 = sgd_trainer_mlflow(X_train=X_train, y_train=y_train)
    best_model, _ = best_model_selector(
        X_test=X_test, y_test=y_test, model1=model1, model2=model2
    )
    register_model(best_model)
