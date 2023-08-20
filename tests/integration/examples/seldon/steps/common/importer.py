#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
from typing import Tuple

import numpy as np  # type: ignore [import]
import pandas as pd
import requests  # type: ignore [import]
import tensorflow as tf  # type: ignore [import]
from numpy import asarray
from PIL import Image
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


def get_data_from_api():
    url = (
        "https://storage.googleapis.com/zenml-public-bucket/mnist"
        "/mnist_handwritten_test.json"
    )

    df = pd.DataFrame(requests.get(url).json())
    data = df["image"].map(lambda x: np.array(x)).values
    data = np.array([x.reshape(28, 28) for x in data])
    return data


@step(enable_cache=False)
def dynamic_importer() -> Annotated[np.ndarray, "data"]:
    """Downloads the latest data from a mock API."""
    data = get_data_from_api()
    return data


@step(enable_cache=False)
def inference_image_loader(
    img_url: str = "https://github.com/zenml-io/zenml/blob/main/tests/integration/examples/seldon/mnist_example_image.png",
) -> str:
    """Load an image and make it available for inference.

    This step is used to load an image from a URL make as a numpy array and
    dump it as a JSON string.

    Args:
        img_url: URL of the image to load.

    Returns:
        The request body includes a base64 coded image for the inference request.
    """
    response = requests.get(img_url)
    img = Image.open(BytesIO(response.content))
    numpydata = asarray(img)
    input = numpydata.tolist()
    return json.dumps([input])
