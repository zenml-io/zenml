import mlflow
import numpy as np
from sklearn.base import ClassifierMixin
from sklearn.svm import SVC

from zenml.integrations.mlflow.mlflow_step_decorator import enable_mlflow
from zenml.steps import step


@enable_mlflow  # setup MLflow
@step(enable_cache=False)
def svc_trainer_mlflow(
    X_train: np.ndarray,
    y_train: np.ndarray,
) -> ClassifierMixin:
    """Train a sklearn SVC classifier and log to MLflow."""
    mlflow.sklearn.autolog()  # log all model hparams and metrics to MLflow
    model = SVC(gamma=0.001)
    model.fit(X_train, y_train)
    return model
