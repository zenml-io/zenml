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
import os
import tempfile
from typing import Any, Type

from tensorflow import keras

from zenml.artifacts import ModelArtifact
from zenml.io import fileio
from zenml.materializers.base_materializer import BaseMaterializer

DEFAULT_FILENAME = "model.hdf5"


class KerasMaterializer(BaseMaterializer):
    """Materializer to read/write Keras models."""

    ASSOCIATED_TYPES = (keras.Model,)
    ASSOCIATED_ARTIFACT_TYPES = (ModelArtifact,)

    def handle_input(self, data_type: Type[Any]) -> keras.Model:
        """Reads and returns a Keras model after copying it to temporary file.

        Returns:
            A tf.keras.Model model.
        """
        super().handle_input(data_type)
        filepath = os.path.join(self.artifact.uri, DEFAULT_FILENAME)

        # Create a temporary folder
        temp_dir = tempfile.mkdtemp(prefix="zenml-temp-")
        temp_file = os.path.join(str(temp_dir), DEFAULT_FILENAME)

        # Copy from artifact store to temporary file
        fileio.copy(filepath, temp_file)

        # Load the model from the temporary file
        model = keras.models.load_model(temp_file)

        # Cleanup and return
        fileio.rmtree(temp_dir)

        return model

    def handle_return(self, model: keras.Model) -> None:
        """Writes a keras model to the artifact store.

        Args:
            model: A tf.keras.Model model.
        """
        super().handle_return(model)
        filepath = os.path.join(self.artifact.uri, DEFAULT_FILENAME)

        # Create a temporary file to store the model
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".hdf5", delete=False
        ) as f:
            model.save(f.name)
            fileio.copy(f.name, filepath)

        # Close and remove the temporary file
        f.close()
        fileio.remove(f.name)
