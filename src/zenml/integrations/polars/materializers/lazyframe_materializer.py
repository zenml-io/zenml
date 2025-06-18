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
"""Polars LazyFrame materializer."""

import os
from typing import Any, ClassVar, Tuple, Type

import polars as pl

from zenml.enums import ArtifactType
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.utils import io_utils


class PolarsLazyMaterializer(BaseMaterializer):
    """Materializer to read/write Polars LazyFrames."""

    ASSOCIATED_TYPES: ClassVar[Tuple[Type[Any], ...]] = (pl.LazyFrame,)
    ASSOCIATED_ARTIFACT_TYPE = ArtifactType.DATA

    def _get_path_to_file(self, temp_dir: str):
        return os.path.join(temp_dir, "lazyframe.bytes").replace("\\", "/")

    def load(self, data_type: Type[Any]) -> Any:
        """Reads and returns Polars data after copying it to temporary path.

        Args:
            data_type: The type of the data to read.

        Returns:
            A Polars data frame or series.
        """
        with self.get_temporary_directory(delete_at_exit=True) as temp_dir:
            io_utils.copy_dir(self.uri, temp_dir)
            data = pl.LazyFrame.deserialize(self._get_path_to_file(temp_dir))

        return data

    def save(self, data: pl.LazyFrame) -> None:
        """Writes Polars LazyFrame to the artifact store.

        Args:
            data: The data to write.

        Raises:
            TypeError: If the data is not of type pl.LazyFrame.
        """
        # Data type check
        if not isinstance(data, self.ASSOCIATED_TYPES):
            raise TypeError(
                f"Expected data of type {self.ASSOCIATED_TYPES}, "
                f"got {type(data)}"
            )

        with self.get_temporary_directory(delete_at_exit=True) as temp_dir:
            # Write the table to a bytes file dump
            data.serialize(self._get_path_to_file(temp_dir))
            io_utils.copy_dir(temp_dir, self.uri)