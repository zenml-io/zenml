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

import tempfile
from typing import TYPE_CHECKING, Any, ClassVar, Dict, Tuple, Type

from tensorflow import keras
from tensorflow.python.keras.utils.layer_utils import count_params

from zenml.enums import ArtifactType
from zenml.io import fileio
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.utils import io_utils

if TYPE_CHECKING:
    from zenml.metadata.metadata_types import MetadataType


class KerasMaterializer(BaseMaterializer):
    """Materializer to read/write Keras models."""

    ASSOCIATED_TYPES: ClassVar[Tuple[Type[Any], ...]] = (keras.Model,)
    ASSOCIATED_ARTIFACT_TYPE: ClassVar[ArtifactType] = ArtifactType.MODEL

    def load(self, data_type: Type[Any]) -> keras.Model:
        """Reads and returns a Keras model after copying it to temporary path.

        Args:
            data_type: The type of the data to read.

        Returns:
            A tf.keras.Model model.
        """
        # Create a temporary directory to store the model
        temp_dir = tempfile.TemporaryDirectory()

        # Copy from artifact store to temporary directory
        io_utils.copy_dir(self.uri, temp_dir.name)

        # Load the model from the temporary directory
        model = keras.models.load_model(temp_dir.name)

        # Cleanup and return
        fileio.rmtree(temp_dir.name)

        return model

    def save(self, model: keras.Model) -> None:
        """Writes a keras model to the artifact store.

        Args:
            model: A tf.keras.Model model.
        """
        # Create a temporary directory to store the model
        temp_dir = tempfile.TemporaryDirectory()
        model.save(temp_dir.name)
        io_utils.copy_dir(temp_dir.name, self.uri)

        # Remove the temporary directory
        fileio.rmtree(temp_dir.name)

    def extract_metadata(
        self, model: keras.Model
    ) -> Dict[str, "MetadataType"]:
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
