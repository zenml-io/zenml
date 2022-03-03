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
from typing import Any, Type

import tensorflow as tf

from zenml.artifacts import DataArtifact
from zenml.materializers.base_materializer import BaseMaterializer

DEFAULT_FILENAME = "saved_data"


class TensorflowDatasetMaterializer(BaseMaterializer):
    """Materializer to read data to and from tf.data.Dataset."""

    ASSOCIATED_TYPES = (tf.data.Dataset,)
    ASSOCIATED_ARTIFACT_TYPES = (DataArtifact,)

    def handle_input(self, data_type: Type[Any]) -> Any:
        """Reads data into tf.data.Dataset"""
        super().handle_input(data_type)
        path = os.path.join(self.artifact.uri, DEFAULT_FILENAME)
        return tf.data.experimental.load(path)

    def handle_return(self, dataset: tf.data.Dataset) -> None:
        """Persists a tf.data.Dataset object."""
        super().handle_return(dataset)
        path = os.path.join(self.artifact.uri, DEFAULT_FILENAME)
        tf.data.experimental.save(
            dataset, path, compression=None, shard_func=None
        )
