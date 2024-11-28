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
from typing import TYPE_CHECKING, Any, ClassVar, Dict, Tuple, Type

import tensorflow as tf

from zenml.enums import ArtifactType
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.utils import io_utils

if TYPE_CHECKING:
    from zenml.metadata.metadata_types import MetadataType

DEFAULT_FILENAME = "saved_data"


class TensorflowDatasetMaterializer(BaseMaterializer):
    """Materializer to read data to and from tf.data.Dataset."""

    ASSOCIATED_TYPES: ClassVar[Tuple[Type[Any], ...]] = (tf.data.Dataset,)
    ASSOCIATED_ARTIFACT_TYPE: ClassVar[ArtifactType] = ArtifactType.DATA

    def load(self, data_type: Type[Any]) -> Any:
        """Reads data into tf.data.Dataset.

        Args:
            data_type: The type of the data to read.

        Returns:
            A tf.data.Dataset object.
        """
        with self.get_temporary_directory(delete_at_exit=False) as temp_dir:
            io_utils.copy_dir(self.uri, temp_dir)
            path = os.path.join(temp_dir, DEFAULT_FILENAME)
            dataset = tf.data.Dataset.load(path)
            return dataset

    def save(self, dataset: tf.data.Dataset) -> None:
        """Persists a tf.data.Dataset object.

        Args:
            dataset: The dataset to persist.
        """
        with self.get_temporary_directory(delete_at_exit=True) as temp_dir:
            path = os.path.join(temp_dir, DEFAULT_FILENAME)
            tf.data.Dataset.save(
                dataset, path, compression=None, shard_func=None
            )
            io_utils.copy_dir(temp_dir, self.uri)

    def extract_metadata(
        self, dataset: tf.data.Dataset
    ) -> Dict[str, "MetadataType"]:
        """Extract metadata from the given `Dataset` object.

        Args:
            dataset: The `Dataset` object to extract metadata from.

        Returns:
            The extracted metadata as a dictionary.
        """
        return {"length": len(dataset)}
