#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Polars materializer."""

import os
import tempfile
from typing import Any, ClassVar, Tuple, Type, Union

import polars as pl
import pyarrow as pa  # type: ignore
import pyarrow.parquet as pq  # type: ignore

from zenml.enums import ArtifactType
from zenml.io import fileio
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.utils import io_utils


class PolarsMaterializer(BaseMaterializer):
    """Materializer to read/write Polars dataframes."""

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

        # If the data is of type pl.Series, convert it back to a pyarrow array
        # instead of a table.
        if (
            table.schema.metadata
            and b"zenml_is_pl_series" in table.schema.metadata
        ):
            isinstance_bytes = table.schema.metadata[b"zenml_is_pl_series"]
            isinstance_series = bool.from_bytes(isinstance_bytes, "big")
            if isinstance_series:
                table = table.column(0)

        # Convert the table to a Polars data frame or series
        data = pl.from_arrow(table)

        # Cleanup and return
        fileio.rmtree(temp_dir.name)

        return data

    def save(self, data: Union[pl.DataFrame, pl.Series]) -> None:
        """Writes Polars data to the artifact store.

        Args:
            data: The data to write.

        Raises:
            TypeError: If the data is not of type pl.DataFrame or pl.Series.
        """
        # Data type check
        if not isinstance(data, self.ASSOCIATED_TYPES):
            raise TypeError(
                f"Expected data of type {self.ASSOCIATED_TYPES}, "
                f"got {type(data)}"
            )

        # Convert the data to an Apache Arrow Table
        if isinstance(data, pl.DataFrame):
            table = data.to_arrow()
        else:
            # Construct a PyArrow Table with schema from the individual pl.Series
            # array if it is a single pl.Series.
            array = data.to_arrow()
            table = pa.Table.from_arrays([array], names=[data.name])

        # Register whether data is of type pl.Series, so that the materializer read step can
        # convert it back appropriately.
        isinstance_bytes = isinstance(data, pl.Series).to_bytes(1, "big")
        table = table.replace_schema_metadata(
            {b"zenml_is_pl_series": isinstance_bytes}
        )

        # Create a temporary directory to store the model
        temp_dir = tempfile.TemporaryDirectory()

        # Write the table to a Parquet file
        path = os.path.join(temp_dir.name, "dataframe.parquet").replace(
            "\\", "/"
        )
        pq.write_table(table, path)  # Uses lz4 compression by default
        io_utils.copy_dir(temp_dir.name, self.uri)

        # Remove the temporary directory
        fileio.rmtree(temp_dir.name)
