#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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


import numpy as np  # type: ignore [import]
from sklearn.base import ClassifierMixin
from sklearn.linear_model import LogisticRegression

from zenml import step


@step
def sklearn_trainer(
    x_train: np.ndarray,
    y_train: np.ndarray,
    solver: str = "saga",
    penalty: str = "l1",
    C: float = 1.0,
    tol: float = 0.1,
) -> ClassifierMixin:
    """Train SVC from sklearn."""
    clf = LogisticRegression(
        penalty=penalty,
        solver=solver,
        tol=tol,
        C=C,
    )
    clf.fit(x_train.reshape((x_train.shape[0], -1)), y_train)
    return clf
