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
import numpy as np
from sklearn.base import ClassifierMixin
from sklearn.svm import SVC

from zenml import step
from zenml.client import Client

step_operator = Client().active_stack.step_operator
if not step_operator:
    raise RuntimeError(
        "Your active stack needs to contain a step operator for this "
        "example "
        "to work."
    )


# setting the step_operator param will tell ZenML
# to run this step on a custom backend defined by the name
# of the operator you provide.
@step(step_operator=step_operator.name)
def remote_trainer(
    X_train: np.ndarray,
    y_train: np.ndarray,
) -> ClassifierMixin:
    """Train a simple sklearn classifier for the digits dataset."""
    model = SVC(gamma=0.001)
    model.fit(X_train, y_train)
    return model
