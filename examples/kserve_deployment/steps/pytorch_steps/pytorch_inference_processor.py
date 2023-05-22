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
import base64
import json
from typing import Optional
from urllib.request import urlopen

from zenml import step
from zenml.steps import BaseParameters


class PyTorchInferenceProcessorStepParameters(BaseParameters):
    """
    Configuration for the PyTorch inference preprocessor step."""

    img_url: Optional[
        str
    ] = "https://raw.githubusercontent.com/kserve/kserve/master/docs/samples/v1beta1/torchserve/v1/imgconv/1.png"


@step(enable_cache=False)
def pytorch_inference_processor(
    params: PyTorchInferenceProcessorStepParameters,
) -> str:
    """Load an image from a URL and encode it as a base64 string.

    Args:
        config: The configuration for the step.

    Returns:
        The request body includes a base64 coded image for the inference request.
    """
    img = urlopen(params.img_url).read()
    image_64_encode = base64.b64encode(img)
    bytes_array = image_64_encode.decode("utf-8")
    instances = {"data": bytes_array}
    request = [instances]
    return json.dumps(request)
