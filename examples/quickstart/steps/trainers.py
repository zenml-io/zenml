import mlflow
import pandas as pd
from sklearn.base import ClassifierMixin
from sklearn.svm import SVC

from zenml.steps import step


@step(enable_cache=False, experiment_tracker="mlflow_tracker")
def svc_trainer_mlflow(
    X_train: pd.DataFrame,
    y_train: pd.Series,
) -> ClassifierMixin:
    """Train a sklearn SVC classifier and log to MLflow."""
    mlflow.sklearn.autolog()  # log all model hparams and metrics to MLflow
    model = SVC(gamma=0.01)
    model.fit(X_train.to_numpy(), y_train.to_numpy())
    train_acc = model.score(X_train.to_numpy(), y_train.to_numpy())
    print(f"Train accuracy: {train_acc}")
    return model
