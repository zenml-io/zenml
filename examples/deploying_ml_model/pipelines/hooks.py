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

"""Deployment initialization and cleanup hooks for churn prediction model."""

from sklearn.pipeline import Pipeline

from zenml.client import Client
from zenml.logger import get_logger

logger = get_logger(__name__)


def init_model(model_name: str = "churn-model") -> Pipeline:
    """Initialize and load the churn prediction model at deployment startup.

    This function runs once when the deployment starts and loads the model
    into memory, making it available for all subsequent inference requests.

    Args:
        model_name: Name of the model artifact to load

    Returns:
        Loaded sklearn Pipeline model

    Raises:
        Exception: If model loading fails
    """
    logger.info(f"Initializing churn prediction model: {model_name}")

    try:
        client = Client()
        model_artifact = client.get_artifact_version(
            name_id_or_prefix=model_name
        )
        model: Pipeline = model_artifact.load()

        logger.info(
            f"Successfully loaded model version: {model_artifact.version}"
        )
        return model

    except Exception as e:
        logger.error(f"Failed to initialize model '{model_name}': {e}")
        raise


def cleanup_model() -> None:
    """Clean up model resources when deployment stops.

    Note: The cleanup hook takes no arguments according to ZenML's hook specification.
    """
    logger.info("Cleaning up churn prediction model resources")
