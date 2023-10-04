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
import torch
import torchvision
from torch.nn.functional import softmax

Array_Like = Union[np.ndarray, List[Any], str, bytes, Dict[str, Any]]


def pre_process(tensor: torch.Tensor) -> dict:
    """Pre process the data to be used for prediction.

    Args:
        tensor (torch.Tensor): The tensor to pre process

    Returns:
        dict: The processed data, in this case a dictionary with the tensor as value.
    """
    tansformation = torchvision.transforms.Normalize((0.1307,), (0.3081,))
    processed_tensor = tansformation(tensor.to(torch.float))
    processed_tensor = processed_tensor.unsqueeze(0)
    return processed_tensor.float()


def post_process(prediction: torch.Tensor) -> str:
    """Pre process the data.

    Args:
        tensor (torch.Tensor): The tensor to pre process

    Returns:
        str: The processed data, in this case the predicted digit.
    """
    classes = [str(i) for i in range(10)]
    prediction = softmax(prediction)
    maxindex = np.argmax(prediction.detach().numpy())
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
        instance = np.array(instance)
        try:
            tensor = torch.from_numpy(instance).view(-1, 28, 28)
        except Exception as e:
            raise TypeError(f"The input instance is not a numpy array. {e}")
        processed_tensor = pre_process(tensor)
        prediction = model(processed_tensor)
        postprocessed_prediction = post_process(prediction)
        inputs.append(postprocessed_prediction)
    return inputs
