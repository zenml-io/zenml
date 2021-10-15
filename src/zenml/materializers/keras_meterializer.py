#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.

from typing import Type

from tensorflow import keras

from zenml.materializers.base_materializer import BaseMaterializer

DEFAULT_FILENAME = "model.hdf5"


class KerasMaterializer(BaseMaterializer):
    """Materializer to read/write Keras models."""

    ASSOCIATED_TYPES = [keras.Model]

    def handle_input(self, data_type: Type) -> keras.Model:
        """Reads and returns a Keras model.

        Returns:
            A tf.keras.Model model.
        """
        super().handle_input(data_type)
        return keras.models.load_model(self.artifact.uri)

    def handle_return(self, model: keras.Model):
        """Writes a keras model.

        Args:
            model: A tf.keras.Model model.
        """
        super().handle_return(model)
        model.save(self.artifact.uri)
