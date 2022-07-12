#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.

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
