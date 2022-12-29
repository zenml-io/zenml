import numpy as np
from sklearn.ensemble import RandomForestClassifier

from zenml.steps.base_parameters import BaseParameters
from zenml.steps.step_decorator import step


class RandomForestClassifierParameters(BaseParameters):
    """Parameters for Random Forest Classifier step"""

    n_estimators: int = 100
    criterion: str = "gini"
    max_depth: int = None


@step
def train_and_predict_rf_classifier(
    params: RandomForestClassifierParameters,
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val: np.ndarray,
) -> np.ndarray:
    """Trains a random forest classifier over the training data and predicts over the validation data"""
    return _train_and_predict_rf_classifier(
        dict(params), X_train, y_train, X_val
    )


@step
def train_and_predict_best_rf_classifier(
    best_model_parameters: dict,
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_test: np.ndarray,
) -> np.ndarray:
    """Trains a random forest classifier over the training data with the model parameters given in the input
    and predicts over the test data"""
    return _train_and_predict_rf_classifier(
        best_model_parameters, X_train, y_train, X_test
    )


def _train_and_predict_rf_classifier(
    parameters: dict,
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_test: np.ndarray,
) -> np.ndarray:
    clf = RandomForestClassifier(**parameters)
    clf.fit(X_train, y_train)
    return clf.predict(X_test)
