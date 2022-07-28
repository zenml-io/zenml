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

from typing import Any, Dict, List

import numpy as np
import torch
import torchvision
from torch.nn.functional import softmax


def pre_process(tensor: torch.Tensor) -> dict:
    """Pre process the data
    Args:
        tensor (torch.Tensor): The tensor to pre process
    Returns:
        dict: The processed data
    """

    tansformation = torchvision.transforms.Normalize((0.1307,), (0.3081,))
    processed_tensor = tansformation(tensor.to(torch.float))
    processed_tensor = processed_tensor.unsqueeze(0)
    return processed_tensor.float()


def custom_predict(model: Any, request: Dict) -> List:
    """Predict the given request.

    The custom predict function is the core of the custom deployment, the function must be expecting a request
    and a model object loaded from the model path. The function must return a response with the prediction.

    Args:
        model (Any): The model to use for prediction.
        request: The request to predict in a dictionary. e.g. {"instances": []}

    Returns:
        The prediction in a dictionary. e.g. {"predictions": []}

    Raises:
        Exception: If the request is not a NumPy array.
    """
    inputs = []
    for instance in request["instances"]:
        instance = np.array(instance)
        try:
            tensor = torch.from_numpy(instance).view(-1, 28, 28)
        except Exception as e:
            raise TypeError(f"The input instance is not a numpy array. {e}")
        processed_tensor = pre_process(tensor)
        prediction = softmax(model(processed_tensor))
        inputs.append(prediction.tolist())
    return inputs
