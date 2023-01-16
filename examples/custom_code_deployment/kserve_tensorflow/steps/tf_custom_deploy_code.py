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

from typing import Any, Dict, List, Union

import numpy as np
import tensorflow as tf  # type: ignore [import]

from zenml.logger import get_logger

logger = get_logger(__name__)

Array_Like = Union[np.ndarray, List[Any], str, bytes, Dict[str, Any]]


def pre_process(input: np.ndarray) -> np.ndarray:
    """Pre process the data to be used for prediction.

    Args:
        input (np.ndarray): The input to pre process

    Returns:
        np.ndarray: The pre processed input
    """
    input = input / 255.0
    return input[None, :, :]


def post_process(prediction: np.ndarray) -> str:
    """Pre process the data.

    Args:
        prediction (np.ndarray): The input array to post process

    Returns:
        str: The processed data, in this case the predicted digit.
    """
    classes = [str(i) for i in range(10)]
    prediction = tf.nn.softmax(prediction, axis=-1)
    maxindex = np.argmax(prediction.numpy())
    return classes[maxindex]


def custom_predict(
    model: Any,
    request: Array_Like,
) -> Array_Like:
    """Custom Prediction function.

    The custom predict function is the core of the custom deployment, the function
    is called by the custom deployment class defined for the serving tool.
    The current implementation requires the function to get the model loaded in the memory and
    a request with the data to predict.

    Args:
        model (Any): The model to use for prediction.
        request: The prediction response of the model is an Array_Like object.

    Returns:
        The prediction in an Array_Like. (e.g: np.ndarray, List[Any], str, bytes, Dict[str, Any])

    Raises:
        Exception: If the request is not a NumPy array.
    """
    inputs = []
    for instance in request:
        input = np.array(instance)
        if not isinstance(input, np.ndarray):
            raise Exception("The request must be a NumPy array")
        processed_input = pre_process(input)
        prediction = model.predict(processed_input)
        postprocessed_prediction = post_process(prediction)
        inputs.append(postprocessed_prediction)
    return inputs
