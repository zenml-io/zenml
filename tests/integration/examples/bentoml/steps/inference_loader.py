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
import os
from typing import Dict, List

from numpy import asarray
from PIL import Image

from zenml import step


@step(enable_cache=False)
def inference_loader() -> Dict[str, List]:
    """Load an image and make it available for inference.

    This step is used to load an image from a URL make as a numpy array and
    dump it as a JSON string.

    Args:
        params: The parameters for the step.

    Returns:
        The request body includes a base64 coded image for the inference request.
    """
    # get the path/directory
    folder_dir = "./inference_samples"

    images = {}
    for image in os.listdir(folder_dir):
        # check if the image ends with png
        img = Image.open(os.path.join(folder_dir, image))
        numpydata = asarray(img)
        input = numpydata.tolist()
        images[image] = input
    return images
