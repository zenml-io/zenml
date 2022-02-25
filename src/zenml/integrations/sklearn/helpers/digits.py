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

from typing import TYPE_CHECKING, Tuple

import numpy as np
from sklearn.base import ClassifierMixin
from sklearn.datasets import load_digits
from sklearn.model_selection import train_test_split
from sklearn.svm import SVC

if TYPE_CHECKING:
    from numpy.typing import NDArray


def get_digits() -> Tuple[
    "NDArray[np.float64]",
    "NDArray[np.float64]",
    "NDArray[np.int64]",
    "NDArray[np.int64]",
]:
    """Returns the digits dataset in the form of a tuple of numpy
    arrays."""
    digits = load_digits()
    # flatten the images
    n_samples = len(digits.images)
    data = digits.images.reshape((n_samples, -1))

    # Split data into 50% train and 50% test subsets
    X_train, X_test, y_train, y_test = train_test_split(
        data, digits.target, test_size=0.5, shuffle=False
    )
    return X_train, X_test, y_train, y_test


def get_digits_model() -> ClassifierMixin:
    """Creates a support vector classifier for digits dataset."""
    return SVC(gamma=0.001)
