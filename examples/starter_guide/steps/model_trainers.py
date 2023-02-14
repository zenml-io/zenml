# Apache Software License 2.0
#
# Copyright (c) ZenML GmbH 2023. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import pandas as pd

from sklearn.base import ClassifierMixin

from zenml.logger import get_logger
from zenml.steps import (
    BaseParameters,
    step,
)

logger = get_logger(__name__)


class SVCTrainerParams(BaseParameters):
    """Trainer params"""
    gamma: float = 0.001
    
@step
def simple_svc_trainer(
    train_set: pd.DataFrame,
    test_set: pd.DataFrame,
) -> ClassifierMixin:
    """Trains a sklearn SVC classifier."""
    X_train, y_train = train_set.drop("target", axis=1), train_set["target"]
    X_test, y_test = test_set.drop("target", axis=1), test_set["target"]
    model = SVC(gamma=0.001)
    model.fit(X_train, y_train)
    test_acc = model.score(X_test, y_test)
    print(f"Test accuracy: {test_acc}")
    return model

@step
def parameterized_svc_trainer(
    params: SVCTrainerParams,
    train_set: pd.DataFrame,
    test_set: pd.DataFrame,
) -> ClassifierMixin:
    """Train a sklearn SVC classifier with hyper-parameters."""
    X_train, y_train = train_set.drop("target", axis=1), train_set["target"]
    X_test, y_test = test_set.drop("target", axis=1), test_set["target"]
    model = SVC(gamma=params.gamma) # Parameterized!
    model.fit(X_train, y_train)
    test_acc = model.score(X_test, y_test)
    print(f"Test accuracy: {test_acc}")
    return model
