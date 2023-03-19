#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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
import pandas as pd

from zenml.config.resource_configuration import ResourceConfiguration
from zenml.integrations.sklearn.helpers.digits import get_digits
from zenml.steps import Output, step


@step(
    resource_configuration=ResourceConfiguration(cpu_count=1, memory="256MB")
)
def importer() -> Output(
    X_train=np.ndarray,
    X_test=np.ndarray,
    y_train=np.ndarray,
    y_test=np.ndarray,
):
    """Loads the digits array as normal numpy arrays."""
    X_train, X_test, y_train, y_test = get_digits()
    return X_train, X_test, y_train, y_test


@step
def get_reference_data(
    X_train: np.ndarray,
    X_test: np.ndarray,
) -> Output(reference=pd.DataFrame, comparison=pd.DataFrame):
    """Splits data for drift detection."""
    columns = [str(x) for x in list(range(X_train.shape[1]))]
    return pd.DataFrame(X_test, columns=columns), pd.DataFrame(
        X_train, columns=columns
    )
