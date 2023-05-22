#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
import json
from io import BytesIO
from typing import Optional

import numpy as np
import requests
from PIL import Image

from zenml import step
from zenml.steps import BaseParameters


class TensorflowInferenceProcessorStepParameters(BaseParameters):
    """Parameters for the PyTorch inference preprocessor step."""

    img_url: Optional[
        str
    ] = "https://raw.githubusercontent.com/kserve/kserve/master/docs/samples/v1beta1/torchserve/v1/imgconv/0.png"


@step(enable_cache=False)
def tf_predict_preprocessor(
    params: TensorflowInferenceProcessorStepParameters,
) -> str:
    """Load an image from a URL and encode it as a base64 string.

    Args:
        config: The configuration for the step.

    Returns:
        The request body includes a base64 coded image for the inference request.
    """
    res = requests.get(params.img_url)
    img_arr = np.array(Image.open(BytesIO(res.content)))
    img_array = img_arr.reshape((-1, 28, 28))
    instances = img_array.tolist()
    request = [instances]
    return json.dumps(request)
