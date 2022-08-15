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

import numpy as np  # type: ignore [import]
import tensorflow as tf  # type: ignore [import]

from zenml.steps import step


@step
def tf_evaluator(
    test_loader: Tuple[np.ndarray, np.ndarray],
    model: tf.keras.Model,
) -> float:
    """Calculate the loss for the model for each epoch in a graph"""
    x_test, y_test = test_loader
    x_test = np.asarray(x_test)
    y_test = np.asarray(y_test)
    _, test_acc = model.evaluate(x_test, y_test, verbose=2)
    return test_acc
