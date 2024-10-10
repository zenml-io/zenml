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
from typing import Dict, List, Union

import numpy as np
from rich import print as rich_print

from zenml import step
from zenml.integrations.bentoml.services import BentoMLLocalDeploymentService
from zenml.integrations.bentoml.services.bentoml_container_deployment import (
    BentoMLContainerDeploymentService,
)


@step
def predictor(
    inference_data: Dict[str, List],
    service: Union[
        BentoMLLocalDeploymentService, BentoMLContainerDeploymentService
    ],
) -> None:
    """Run an inference request against the BentoML prediction service.

    Args:
        service: The BentoML service.
        data: The data to predict.
    """
    if not service.is_running:
        service.start(timeout=10)  # should be a NOP if already started
    for img, data in inference_data.items():
        grayscale_image = np.dot(
            np.array(data)[..., :3], [0.2989, 0.5870, 0.1140]
        )
        grayscale_image = grayscale_image.astype(np.uint8)
        prediction = service.predict("predict_ndarray", grayscale_image)
        result = to_labels(prediction[0])
        rich_print(f"Prediction for {img} is {result}")


def to_labels(prediction: List[float]) -> str:
    """Converts a prediction to a list of labels.

    Args:
        prediction: The prediction.

    Returns:
        The list of labels.
    """
    labels = [
        "T-shirt/top",
        "Trouser",
        "Pullover",
        "Dress",
        "Coat",
        "Sandal",
        "Shirt",
        "Sneaker",
        "Bag",
        "Ankle boot",
    ]
    return labels[np.argmax(prediction, axis=0)]
