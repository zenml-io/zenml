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
from typing import Tuple

import numpy as np
import tensorflow as tf
from typing_extensions import Annotated

from zenml import step


@step
def importer() -> (
    Tuple[
        Annotated[np.ndarray, "X_train"],
        Annotated[np.ndarray, "X_test"],
        Annotated[np.ndarray, "y_train"],
        Annotated[np.ndarray, "y_test"],
    ]
):
    """Download the MNIST data store it as an artifact."""
    train, test = tf.keras.datasets.mnist.load_data()
    (X_train, y_train), (X_test, y_test) = train, test
    return X_train, X_test, y_train, y_test
