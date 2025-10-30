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

"""Custom materializer for Ultralytics YOLO models.

This materializer handles YOLO model objects by storing their weights file
and allowing them to be reconstructed in subsequent pipeline steps.
"""

import os
from typing import Any, ClassVar, Optional, Tuple, Type

from ultralytics import YOLO

from zenml.enums import ArtifactType
from zenml.io import fileio
from zenml.materializers.base_materializer import BaseMaterializer


class UltralyticsYOLOMaterializer(BaseMaterializer):
    """Materializer for Ultralytics YOLO model objects.

    This materializer stores YOLO model weights and allows the model to be
    loaded back for inference or further training. It handles the serialization
    of the model weights file to the artifact store.
    """

    ASSOCIATED_TYPES: ClassVar[Tuple[Type[Any], ...]] = (YOLO,)
    ASSOCIATED_ARTIFACT_TYPE: ClassVar[ArtifactType] = ArtifactType.MODEL
    MODEL_FILENAME: ClassVar[str] = "model.pt"

    def _get_best_weights_path(self, model: YOLO) -> Optional[str]:
        """Get the best weights path from a trained YOLO model.

        Args:
            model: The YOLO model

        Returns:
            Path to the best weights if available, None otherwise
        """
        # Prefer trained best weights from trainer
        if (
            hasattr(model, "trainer")
            and model.trainer
            and hasattr(model.trainer, "best")
        ):
            best_path = getattr(model.trainer, "best", None)
            if best_path and os.path.exists(best_path):
                return best_path

        # Fallback to ckpt_path if it exists
        if (
            hasattr(model, "ckpt_path")
            and model.ckpt_path
            and os.path.exists(model.ckpt_path)
        ):
            return model.ckpt_path

        return None

    def load(self, data_type: Type[YOLO]) -> YOLO:
        """Load a YOLO model from the artifact store.

        Args:
            data_type: The YOLO model type

        Returns:
            The loaded YOLO model

        Raises:
            FileNotFoundError: If the model weights file cannot be found
        """
        # Get the path to the stored weights file
        weights_path = os.path.join(self.uri, self.MODEL_FILENAME)

        if not fileio.exists(weights_path):
            raise FileNotFoundError(
                f"Could not find YOLO model weights at {weights_path}"
            )

        # Download weights to a temporary location
        with self.get_temporary_directory(delete_at_exit=True) as temp_dir:
            local_weights_path = os.path.join(temp_dir, self.MODEL_FILENAME)
            fileio.copy(weights_path, local_weights_path)

            # Load the YOLO model from the weights file
            model = YOLO(local_weights_path)

            return model

    def save(self, model: YOLO) -> None:
        """Save a YOLO model to the artifact store.

        Args:
            model: The YOLO model to save
        """
        # Try to get the best weights path from trained model
        source_weights_path = self._get_best_weights_path(model)

        if not source_weights_path:
            # Fallback: export the model to get weights
            with self.get_temporary_directory(delete_at_exit=True) as temp_dir:
                temp_weights = os.path.join(temp_dir, self.MODEL_FILENAME)
                # Save model weights to temporary location
                model.save(temp_weights)
                source_weights_path = temp_weights

        if not source_weights_path or not os.path.exists(source_weights_path):
            raise FileNotFoundError(
                "Could not locate or create YOLO model weights. "
                "Ensure the model has been trained or weights are available."
            )

        # Ensure destination directory exists
        if not fileio.exists(self.uri):
            fileio.makedirs(self.uri)

        # Copy weights to artifact store
        destination_path = os.path.join(self.uri, self.MODEL_FILENAME)
        fileio.copy(str(source_weights_path), destination_path)
