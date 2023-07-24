import mlflow
import pandas as pd
from sklearn.base import ClassifierMixin
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import SGDClassifier

from zenml import step
from zenml.client import Client

experiment_tracker = Client().active_stack.experiment_tracker


@step(experiment_tracker=experiment_tracker.name)
def random_forest_trainer_mlflow(
    X_train: pd.DataFrame,
    y_train: pd.Series,
) -> ClassifierMixin:
    """Train a sklearn Random Forest classifier and log to MLflow."""
    mlflow.sklearn.autolog()  # log all model hyperparams and metrics to MLflow
    model = RandomForestClassifier()
    model.fit(X_train.to_numpy(), y_train.to_numpy())
    train_acc = model.score(X_train.to_numpy(), y_train.to_numpy())
    print(f"Train accuracy: {train_acc}")
    return model


@step(experiment_tracker=experiment_tracker.name)
def sgd_trainer_mlflow(
    X_train: pd.DataFrame,
    y_train: pd.Series,
) -> ClassifierMixin:
    """Train a SGD classifier and log to MLflow."""
    mlflow.sklearn.autolog()  # log all model hyperparams and metrics to MLflow
    model = SGDClassifier()
    model.fit(X_train.to_numpy(), y_train.to_numpy())
    train_acc = model.score(X_train.to_numpy(), y_train.to_numpy())
    print(f"Train accuracy: {train_acc}")
    return model
