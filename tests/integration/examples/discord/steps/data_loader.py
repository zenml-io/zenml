#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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

from typing import Tuple
from typing_extensions import Annotated
import numpy as np
from sklearn.datasets import load_digits
from sklearn.model_selection import train_test_split

from zenml import step


@step
def digits_data_loader() -> (
    Tuple[
        Annotated[np.ndarray, "X_train"],
        Annotated[np.ndarray, "X_test"],
        Annotated[np.ndarray, "y_train"],
        Annotated[np.ndarray, "y_test"]
    ]
):
    """Loads the digits dataset as a tuple of flattened numpy arrays."""
    digits = load_digits()
    data = digits.images.reshape((len(digits.images), -1))
    X_train, X_test, y_train, y_test = train_test_split(
        data, digits.target, test_size=0.2, shuffle=False
    )
    return X_train, X_test, y_train, y_test
