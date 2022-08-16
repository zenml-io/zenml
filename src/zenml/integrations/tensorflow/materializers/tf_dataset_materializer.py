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
"""Implementation of the TensorFlow dataset materializer."""

import os
import tempfile
from typing import Any, Type

import tensorflow as tf

from zenml.artifacts import DataArtifact
from zenml.io import fileio
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.utils import io_utils

DEFAULT_FILENAME = "saved_data"


class TensorflowDatasetMaterializer(BaseMaterializer):
    """Materializer to read data to and from tf.data.Dataset."""

    ASSOCIATED_TYPES = (tf.data.Dataset,)
    ASSOCIATED_ARTIFACT_TYPES = (DataArtifact,)

    def handle_input(self, data_type: Type[Any]) -> Any:
        """Reads data into tf.data.Dataset.

        Args:
            data_type: The type of the data to read.

        Returns:
            A tf.data.Dataset object.
        """
        super().handle_input(data_type)
        temp_dir = tempfile.TemporaryDirectory()
        try:
            io_utils.copy_dir(self.artifact.uri, temp_dir.name)
            path = os.path.join(temp_dir.name, DEFAULT_FILENAME)
            dataset = tf.data.experimental.load(path)
        finally:
            fileio.rmtree(temp_dir.name)

        return dataset

    def handle_return(self, dataset: tf.data.Dataset) -> None:
        """Persists a tf.data.Dataset object.

        Args:
            dataset: The dataset to persist.
        """
        super().handle_return(dataset)
        temp_dir = tempfile.TemporaryDirectory()
        path = os.path.join(temp_dir.name, DEFAULT_FILENAME)
        try:
            tf.data.experimental.save(
                dataset, path, compression=None, shard_func=None
            )
            io_utils.copy_dir(temp_dir.name, self.artifact.uri)
        finally:
            fileio.rmtree(temp_dir.name)
