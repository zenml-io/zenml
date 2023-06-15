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
import numpy as np  # type: ignore [import]
import tensorflow as tf  # type: ignore [import]

from zenml import step
from zenml.steps import Output


@step
def importer_mnist() -> (
    Output(
        x_train=np.ndarray,
        y_train=np.ndarray,
        x_test=np.ndarray,
        y_test=np.ndarray,
    )
):
    """Download the MNIST data store it as an artifact."""
    (x_train, y_train), (
        x_test,
        y_test,
    ) = tf.keras.datasets.mnist.load_data()
    return x_train, y_train, x_test, y_test
