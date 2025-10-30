# Apache Software License 2.0
#
# Copyright (c) ZenML GmbH 2025. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Deployment initialization and cleanup hooks for YOLO model.

These hooks implement the "warm container" pattern, where the model is loaded
once at deployment startup and kept in memory for fast inference. This eliminates
cold-start delays and provides sub-second inference times.
"""

from ultralytics import YOLO

from zenml.client import Client
from zenml.logger import get_logger

logger = get_logger(__name__)


def init_model(model_name: str = "yolo-model") -> YOLO:
    """Initialize and load the YOLO model at deployment startup.

    This function runs once when the deployment starts and loads the YOLO model
    into memory, making it available for all subsequent inference requests.
    The model stays "warm" throughout the deployment lifetime.

    Args:
        model_name: Name of the model artifact to load

    Returns:
        Loaded YOLO model instance

    Raises:
        Exception: If model loading fails
    """
    logger.info(f"Initializing YOLO model: {model_name}")

    try:
        client = Client()
        model_artifact = client.get_artifact_version(
            name_id_or_prefix=model_name
        )
        model: YOLO = model_artifact.load()

        logger.info(
            f"Successfully loaded YOLO model version: {model_artifact.version}"
        )
        logger.info("Model is warm and ready for inference!")

        return model

    except Exception as e:
        logger.error(f"Failed to initialize model '{model_name}': {e}")
        logger.error(
            "Make sure you've trained the model with: python run.py --train"
        )
        raise


def cleanup_model() -> None:
    """Clean up model resources when deployment stops.

    This function is called when the deployment shuts down. It can be used
    to release any resources held by the model.

    Note: The cleanup hook takes no arguments according to ZenML's hook specification.
    """
    logger.info("Cleaning up YOLO model resources")
