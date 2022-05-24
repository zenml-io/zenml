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
import tempfile
from typing import Any, Type

from tensorflow import keras

from zenml.artifacts import ModelArtifact
from zenml.io import fileio
from zenml.io import utils as fileio_utils
from zenml.materializers.base_materializer import BaseMaterializer


class KerasMaterializer(BaseMaterializer):
    """Materializer to read/write Keras models."""

    ASSOCIATED_TYPES = (keras.Model,)
    ASSOCIATED_ARTIFACT_TYPES = (ModelArtifact,)

    def handle_input(self, data_type: Type[Any]) -> keras.Model:
        """Reads and returns a Keras model after copying it to temporary path.

        Returns:
            A tf.keras.Model model.
        """
        super().handle_input(data_type)

        # Create a temporary directory to store the model
        temp_dir = tempfile.TemporaryDirectory()

        # Copy from artifact store to temporary directory
        fileio_utils.copy_dir(self.artifact.uri, temp_dir.name)

        # Load the model from the temporary directory
        model = keras.models.load_model(temp_dir.name)

        # Cleanup and return
        fileio.rmtree(temp_dir.name)

        return model

    def handle_return(self, model: keras.Model) -> None:
        """Writes a keras model to the artifact store.

        Args:
            model: A tf.keras.Model model.
        """
        super().handle_return(model)

        # Create a temporary directory to store the model
        temp_dir = tempfile.TemporaryDirectory()
        model.save(temp_dir.name)
        fileio_utils.copy_dir(temp_dir.name, self.artifact.uri)

        # Remove the temporary directory
        fileio.rmtree(temp_dir.name)
