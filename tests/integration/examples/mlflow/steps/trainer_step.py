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
from sklearn.svm import SVC

from zenml import step
from zenml.client import Client
from zenml.integrations.mlflow.experiment_trackers import (
    MLFlowExperimentTracker,
)

experiment_tracker = Client().active_stack.experiment_tracker

if not experiment_tracker or not isinstance(
    experiment_tracker, MLFlowExperimentTracker
):
    raise RuntimeError(
        "Your active stack needs to contain a MLFlow experiment tracker for "
        "this example to work."
    )


@step(experiment_tracker=experiment_tracker.name)
def trainer(
    X_train: np.ndarray,
    y_train: np.ndarray,
) -> SVC:
    """Train an SVC Classifier to recognize MNIST digits return our
    model or the learner."""
    model = SVC(gamma=0.001)

    mlflow.sklearn.autolog()
    model.fit(
        X_train,
        y_train,
    )

    # write model
    return model
