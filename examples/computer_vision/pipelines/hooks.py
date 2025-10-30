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


def init_model(model_tag: str = "production") -> YOLO:
    """Initialize and load the YOLO model at deployment startup.

    This function runs once when the deployment starts and loads the YOLO model
    into memory, making it available for all subsequent inference requests.
    The model stays "warm" throughout the deployment lifetime.

    Args:
        model_tag: Tag to filter model artifacts (default: "production")

    Returns:
        Loaded YOLO model instance

    Raises:
        Exception: If model loading fails
    """
    logger.info(f"Initializing YOLO model with tag: {model_tag}")

    try:
        client = Client()

        # Load the latest model artifact tagged with the specified tag
        # This retrieves the trained model from the training pipeline
        model_artifacts = client.list_artifact_versions(
            name="yolo-model",
            tag=model_tag,
            sort_by="created",
            size=1,
        )

        if not model_artifacts.items:
            raise ValueError(
                f"No model artifacts found with name 'yolo-model' and tag '{model_tag}'. "
                f"Train a model first with: python run.py --train"
            )

        model_artifact = model_artifacts.items[0]

        # Load the YOLO model directly
        # The UltralyticsYOLOMaterializer handles converting the stored weights to a YOLO object
        model: YOLO = model_artifact.load()

        logger.info(
            f"Successfully loaded YOLO model version: {model_artifact.version}"
        )
        logger.info(f"Model tags: {[tag.name for tag in model_artifact.tags]}")
        logger.info("Model is warm and ready for inference!")

        return model

    except Exception as e:
        logger.error(f"Failed to initialize model with tag '{model_tag}': {e}")
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
    # YOLO models don't require explicit cleanup, but this hook is available
    # if needed (e.g., closing file handles, releasing GPU memory, etc.)
