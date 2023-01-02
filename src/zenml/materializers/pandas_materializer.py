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
"""Materializer for Pandas."""

import os
import tempfile
from typing import Any, Type, Union

import pandas as pd

from zenml.enums import ArtifactType
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.materializers.base_materializer import BaseMaterializer

logger = get_logger(__name__)

PARQUET_FILENAME = "df.parquet.gzip"
COMPRESSION_TYPE = "gzip"

CSV_FILENAME = "df.csv"


class PandasMaterializer(BaseMaterializer):
    """Materializer to read data to and from pandas."""

    ASSOCIATED_TYPES = (pd.DataFrame, pd.Series)
    ASSOCIATED_ARTIFACT_TYPE = ArtifactType.DATA

    def __init__(self, uri: str):
        """Define `self.data_path`.

        Args:
            uri: The URI where the artifact data is stored.
        """
        super().__init__(uri)
        try:
            import pyarrow  # type: ignore

            self.pyarrow_exists = True
        except ImportError:
            self.pyarrow_exists = False
            logger.warning(
                "By default, the `PandasMaterializer` stores data as a "
                "`.csv` file. If you want to store data more efficiently, "
                "you can install `pyarrow` by running "
                "'`pip install pyarrow`'. This will allow `PandasMaterializer` "
                "to automatically store the data as a `.parquet` file instead."
            )
        finally:
            self.parquet_path = os.path.join(self.uri, PARQUET_FILENAME)
            self.csv_path = os.path.join(self.uri, CSV_FILENAME)

    def load(self, data_type: Type[Any]) -> Union[pd.DataFrame, pd.Series]:
        """Reads `pd.DataFrame` or `pd.Series` from a `.parquet` or `.csv` file.

        Args:
            data_type: The type of the data to read.

        Raises:
            ImportError: If pyarrow or fastparquet is not installed.

        Returns:
            The pandas dataframe or series.
        """
        super().load(data_type)
        temp_dir = tempfile.mkdtemp(prefix="zenml-temp-")
        if fileio.exists(self.parquet_path):
            if self.pyarrow_exists:
                # Create a temporary file
                temp_file = os.path.join(str(temp_dir), PARQUET_FILENAME)
                # Copy the data to the temporary file
                fileio.copy(self.parquet_path, temp_file)
                # Load the data from the temporary file
                df = pd.read_parquet(temp_file)
            else:
                raise ImportError(
                    "You have an old version of a `PandasMaterializer` "
                    "data artifact stored in the artifact store "
                    "as a `.parquet` file, which requires `pyarrow` "
                    "for reading, You can install `pyarrow` by running "
                    "'`pip install pyarrow fastparquet`'."
                )
        else:
            # Create a temporary file
            temp_file = os.path.join(str(temp_dir), CSV_FILENAME)
            # Copy the data to the temporary file
            fileio.copy(self.csv_path, temp_file)
            # Load the data from the temporary file
            df = pd.read_csv(temp_file, index_col=0, parse_dates=True)

        # Cleanup and return
        fileio.rmtree(temp_dir)

        # validate the type of the data.
        def is_dataframe_or_series(
            df: Union[pd.DataFrame, pd.Series]
        ) -> Union[pd.DataFrame, pd.Series]:
            """Checks if the data is a `pd.DataFrame` or `pd.Series`.

            Args:
                df: The data to check.

            Returns:
                The data if it is a `pd.DataFrame` or `pd.Series`.
            """
            if issubclass(data_type, pd.Series):
                # Taking the first column if its a series as the assumption
                # is that there will only be one
                assert len(df.columns) == 1
                df = df[df.columns[0]]
                return df
            else:
                return df

        return is_dataframe_or_series(df)

    def save(self, df: Union[pd.DataFrame, pd.Series]) -> None:
        """Writes a pandas dataframe or series to the specified filename.

        Args:
            df: The pandas dataframe or series to write.
        """
        super().save(df)

        if isinstance(df, pd.Series):

            df = df.to_frame(name="series")

        # Create a temporary file to store the data
        if self.pyarrow_exists:
            with tempfile.NamedTemporaryFile(
                mode="wb", suffix=".gzip", delete=False
            ) as f:
                df.to_parquet(f.name, compression=COMPRESSION_TYPE)
                fileio.copy(f.name, self.parquet_path)
        else:
            with tempfile.NamedTemporaryFile(
                mode="wb", suffix=".csv", delete=False
            ) as f:
                df.to_csv(f.name, index=True)
                fileio.copy(f.name, self.csv_path)

        # Close and remove the temporary file
        f.close()
        fileio.remove(f.name)
