#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
import numpy as np
from sklearn.ensemble import RandomForestClassifier

from zenml import step
from zenml.steps.base_parameters import BaseParameters


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
    """Trains a random forest classifier over the training data and predicts
    over the validation data"""
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
    """Trains a random forest classifier over the training data with the model
    parameters given in the input and predicts over the test data"""
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
