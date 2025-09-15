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
#

"""Pipeline hooks for model preloading in serving deployments."""

from zenml.client import Client
from zenml.logger import get_logger

logger = get_logger(__name__)


class PipelineState:
    """Pipeline state for serving."""

    def __init__(self) -> None:
        """Initialize the pipeline state."""
        self.model = None
        self.preprocessor = None

        try:
            # Get ZenML client
            client = Client()

            # Get production model version
            model_version = client.get_model_version(
                "breast_cancer_classifier", "production"
            )

            logger.info(
                f"📦 Loading production model: {model_version.name} v{model_version.version}"
            )

            # Preload model artifact
            model_artifact = model_version.get_artifact("sklearn_classifier")
            self.model = model_artifact.load()

            # Preload preprocessing pipeline
            preprocess_artifact = model_version.get_artifact(
                "preprocess_pipeline"
            )
            self.preprocessor = preprocess_artifact.load()

            logger.info("✅ Model and preprocessor loaded successfully")
            logger.info(f"   Model type: {type(self.model).__name__}")
            logger.info(
                f"   Preprocessor type: {type(self.preprocessor).__name__}"
            )

        except Exception as e:
            logger.error(f"❌ Failed to preload model: {e}")
            # Don't raise error to allow pipeline to continue without preloading


def init_hook() -> PipelineState:
    """Initialize the pipeline with preloaded model and preprocessor."""
    logger.info("🚀 Initializing serving pipeline...")
    return PipelineState()
