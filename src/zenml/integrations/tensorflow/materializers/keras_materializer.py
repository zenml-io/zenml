#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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
"""Implementation of the TensorFlow Keras materializer."""

import os
from typing import TYPE_CHECKING, Any, ClassVar

import tensorflow as tf
from tensorflow.python import keras as tf_keras
from tensorflow.python.keras.utils.layer_utils import count_params

from zenml.enums import ArtifactType
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.utils import io_utils

if TYPE_CHECKING:
    from zenml.metadata.metadata_types import MetadataType


class KerasMaterializer(BaseMaterializer):
    """Materializer to read/write Keras models."""

    ASSOCIATED_TYPES: ClassVar[tuple[type[Any], ...]] = (
        tf.keras.Model,
        tf_keras.Model,
    )
    ASSOCIATED_ARTIFACT_TYPE: ClassVar[ArtifactType] = ArtifactType.MODEL
    MODEL_FILE_NAME = "model.keras"

    def load(self, data_type: type[Any]) -> tf_keras.Model:
        """Reads and returns a Keras model after copying it to temporary path.

        Args:
            data_type: The type of the data to read.

        Returns:
            A keras.Model model.
        """
        with self.get_temporary_directory(delete_at_exit=True) as temp_dir:
            # Copy from artifact store to temporary directory
            temp_model_file = os.path.join(temp_dir, self.MODEL_FILE_NAME)
            io_utils.copy_dir(self.uri, temp_dir)

            # Load the model from the temporary directory
            model = tf.keras.models.load_model(temp_model_file)

            return model

    def save(self, model: tf_keras.Model) -> None:
        """Writes a keras model to the artifact store.

        Args:
            model: A keras.Model model.
        """
        with self.get_temporary_directory(delete_at_exit=True) as temp_dir:
            temp_model_file = os.path.join(temp_dir, self.MODEL_FILE_NAME)
            model.save(temp_model_file)
            io_utils.copy_dir(temp_dir, self.uri)

    def extract_metadata(
        self, model: tf_keras.Model
    ) -> dict[str, "MetadataType"]:
        """Extract metadata from the given `Model` object.

        Args:
            model: The `Model` object to extract metadata from.

        Returns:
            The extracted metadata as a dictionary.
        """
        return {
            "num_layers": len(model.layers),
            "num_params": count_params(model.weights),
            "num_trainable_params": count_params(model.trainable_weights),
        }
