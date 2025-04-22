"""This step downloads the latest data from a mock API and returns it as a numpy array."""

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
import numpy as np  # type: ignore [import]
import pandas as pd  # type: ignore [import]
import requests  # type: ignore [import]
from typing_extensions import Annotated

from zenml import step


def get_data_from_api() -> Annotated[np.ndarray, "api_data"]:
    """Downloads the latest data from a mock API.

    Returns:
        Annotated[np.ndarray, "data"]: Downsampled image data as a numpy array.
    """
    url = (
        "https://storage.googleapis.com/zenml-public-bucket/mnist"
        "/mnist_handwritten_test.json"
    )

    df = pd.DataFrame(requests.get(url, timeout=31).json())
    data = df["image"].map(lambda x: np.array(x)).values
    data = np.array(
        [
            # Pad the image to 32x32 to enable downsampling to 8x8
            np.pad(x.reshape(28, 28).astype("float64"), 2)[
                ::4, ::4
            ]  # Downsample to 8x8 by taking every 4th pixel
            for x in data
        ]
    )
    return data


@step(enable_cache=False)
def dynamic_importer() -> Annotated[np.ndarray, "data"]:
    """Downloads the latest data from a mock API.

    Returns:
        Annotated[np.ndarray, "data"]: Downsampled image data as a numpy array.
    """
    data = get_data_from_api()
    return data
