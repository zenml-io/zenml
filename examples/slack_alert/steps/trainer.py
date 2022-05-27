import mlflow
import numpy as np
from sklearn.base import ClassifierMixin
from sklearn.svm import SVC

from zenml.integrations.mlflow.mlflow_step_decorator import enable_mlflow
from zenml.steps import step


@step
def svc_trainer(
    X_train: np.ndarray,
    y_train: np.ndarray,
) -> ClassifierMixin:
    """Train a sklearn SVC classifier."""
    model = SVC(gamma=0.001)
    model.fit(X_train, y_train)
    return model


@enable_mlflow
@step(enable_cache=False)
def svc_trainer_mlflow(
    X_train: np.ndarray,
    y_train: np.ndarray,
) -> ClassifierMixin:
    """Train a sklearn SVC classifier and log to MLflow."""
    mlflow.sklearn.autolog()
    model = SVC(gamma=0.001)
    model.fit(X_train, y_train)
    return model
