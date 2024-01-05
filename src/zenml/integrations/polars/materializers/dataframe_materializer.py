#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""PyCaret materializer."""

import tempfile
from typing import (
    Any,
    Type,
)

import polars as pl
import pyarrow.parquet as pq

from zenml.enums import ArtifactType
from zenml.io import fileio
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.utils import io_utils


class PolarsMaterializer(BaseMaterializer):
    """Materializer to read/write Polar data frames."""

    ASSOCIATED_TYPES: ClassVar[Tuple[Type[Any], ...]] = (
        pl.DataFrame,
        pl.Series,
    )
    ASSOCIATED_ARTIFACT_TYPE = ArtifactType.DATA

    def load(self, data_type: Type[Any]) -> Any:
        """Reads and returns Polars data after copying it to temporary path.

        Args:
            data_type: The type of the data to read.

        Returns:
            A Polars data frame or series.
        """
        # Create a temporary directory to store the model
        temp_dir = tempfile.TemporaryDirectory()

        # Copy from artifact store to temporary directory
        io_utils.copy_dir(self.uri, temp_dir.name)

        # Load the data from the temporary directory
        table = pq.read_table(
            os.path.join(temp_dir.name, "dataframe.parquet").replace("\\", "/")
        )

        # Convert the table to a Polars data frame or series
        data = pl.from_arrow(table)

        # Cleanup and return
        fileio.rmtree(temp_dir.name)

        return data

    def save(self, data: Union[pl.DataFrame, pl.Series]) -> None:
        """Writes Polars data to the artifact store.

        Args:
            model: Any of the supported models.
        """
        # Data type check
        if not isinstance(data, self.ASSOCIATED_TYPES):
            raise TypeError(
                f"Expected data of type {self.ASSOCIATED_TYPES}, "
                f"got {type(data)}"
            )

        # Convert the data to an Apache Arrow Table
        table = data.to_arrow()

        # Create a temporary directory to store the model
        temp_dir = tempfile.TemporaryDirectory()

        # Write the table to a Parquet file
        path = os.path.join(temp_dir.name, "dataframe.parquet").replace("\\", "/")
        pq.write_table(table, path) # Uses lz4 compression by default
        io_utils.copy_dir(temp_dir.name, self.uri)

        # Remove the temporary directory
        fileio.rmtree(temp_dir.name)
