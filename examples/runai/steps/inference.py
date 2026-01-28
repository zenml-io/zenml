#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""Inference step for Run:AI deployer example."""

from typing import Annotated, Dict, List

from zenml import step
from zenml.logger import get_logger

logger = get_logger(__name__)


@step
def predict(
    features: List[float],
) -> Annotated[Dict[str, float], "prediction_result"]:
    """Run inference on input features.

    This step can be deployed as an HTTP endpoint using the Run:AI deployer.
    When deployed, it runs as an inference workload on Run:AI with fractional
    GPU support and autoscaling.

    Args:
        features: List of input features for prediction.

    Returns:
        Dictionary containing prediction results with keys:
        - prediction: Binary prediction (0 or 1)
        - probability: Prediction probability (0.0 to 1.0)
        - num_features: Number of input features processed
    """
    import numpy as np

    logger.info(f"Running inference on {len(features)} features...")

    features_array = np.array(features, dtype=np.float32)

    # Simple mock prediction (in production, load a trained model)
    weights = np.random.RandomState(42).randn(len(features))
    logit = np.dot(features_array, weights)
    probability = 1 / (1 + np.exp(-logit))
    prediction = int(probability > 0.5)

    result = {
        "prediction": float(prediction),
        "probability": float(probability),
        "num_features": float(len(features)),
    }

    logger.info(f"Prediction: {prediction}, Probability: {probability:.4f}")

    return result
