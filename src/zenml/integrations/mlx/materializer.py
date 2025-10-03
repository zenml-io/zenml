#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""Implementation of the ZenML MLX materializer."""

import os
from typing import (
    Any,
    ClassVar,
    Tuple,
    Type,
)

import mlx.core as mx

from zenml.enums import ArtifactType
from zenml.materializers.base_materializer import BaseMaterializer

NUMPY_FILENAME = "data.npy"


class MLXArrayMaterializer(BaseMaterializer):
    """A materializer for MLX arrays."""

    ASSOCIATED_TYPES: ClassVar[Tuple[Type[Any], ...]] = (mx.array,)
    ASSOCIATED_ARTIFACT_TYPE: ClassVar[ArtifactType] = ArtifactType.DATA

    def load(self, data_type: Type[Any]) -> mx.array:
        """Reads data from a `.npy` file, and returns an MLX array.

        Args:
            data_type: The type of the data to read.

        Returns:
            The MLX array.
        """
        numpy_file = os.path.join(self.uri, NUMPY_FILENAME)

        with self.artifact_store.open(numpy_file, "rb") as f:
            # loading an .npy file always results in a single array.
            arr = mx.load(f)
            assert isinstance(arr, mx.array)
            return arr

    def save(self, data: mx.array) -> None:
        """Writes an MLX array to the artifact store as a `.npy` file.

        Args:
            data: The MLX array to write.
        """
        with self.artifact_store.open(
            os.path.join(self.uri, NUMPY_FILENAME), "wb"
        ) as f:
            mx.save(f, data)
