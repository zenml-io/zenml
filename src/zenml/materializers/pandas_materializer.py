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
from typing import Any, ClassVar, Dict, Optional, Tuple, Type, Union

import pandas as pd

from zenml.artifact_stores.base_artifact_store import BaseArtifactStore
from zenml.enums import ArtifactType, VisualizationType
from zenml.logger import get_logger
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.metadata.metadata_types import DType, MetadataType

logger = get_logger(__name__)

PARQUET_FILENAME = "df.parquet.gzip"
COMPRESSION_TYPE = "gzip"

CSV_FILENAME = "df.csv"


class PandasMaterializer(BaseMaterializer):
    """Materializer to read data to and from pandas."""

    ASSOCIATED_TYPES: ClassVar[Tuple[Type[Any], ...]] = (
        pd.DataFrame,
        pd.Series,
    )
    ASSOCIATED_ARTIFACT_TYPE: ClassVar[ArtifactType] = ArtifactType.DATA

    def __init__(
        self, uri: str, artifact_store: Optional[BaseArtifactStore] = None
    ):
        """Define `self.data_path`.

        Args:
            uri: The URI where the artifact data is stored.
            artifact_store: The artifact store where the artifact data is stored.
        """
        super().__init__(uri, artifact_store)
        try:
            import pyarrow  # type: ignore # noqa

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
        if self.artifact_store.exists(self.parquet_path):
            if self.pyarrow_exists:
                with self.artifact_store.open(
                    self.parquet_path, mode="rb"
                ) as f:
                    df = pd.read_parquet(f)
            else:
                raise ImportError(
                    "You have an old version of a `PandasMaterializer` "
                    "data artifact stored in the artifact store "
                    "as a `.parquet` file, which requires `pyarrow` "
                    "for reading, You can install `pyarrow` by running "
                    "'`pip install pyarrow fastparquet`'."
                )
        else:
            with self.artifact_store.open(self.csv_path, mode="rb") as f:
                df = pd.read_csv(f, index_col=0, parse_dates=True)

        # validate the type of the data.
        def is_dataframe_or_series(
            df: Union[pd.DataFrame, pd.Series],
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
        if isinstance(df, pd.Series):
            df = df.to_frame(name="series")

        if self.pyarrow_exists:
            with self.artifact_store.open(self.parquet_path, mode="wb") as f:
                df.to_parquet(f, compression=COMPRESSION_TYPE)
        else:
            with self.artifact_store.open(self.csv_path, mode="wb") as f:
                df.to_csv(f, index=True)

    def save_visualizations(
        self, df: Union[pd.DataFrame, pd.Series]
    ) -> Dict[str, VisualizationType]:
        """Save visualizations of the given pandas dataframe or series.

        Args:
            df: The pandas dataframe or series to visualize.

        Returns:
            A dictionary of visualization URIs and their types.
        """
        describe_uri = os.path.join(self.uri, "describe.csv")
        describe_uri = describe_uri.replace("\\", "/")
        with self.artifact_store.open(describe_uri, mode="wb") as f:
            df.describe().to_csv(f)
        return {describe_uri: VisualizationType.CSV}

    def extract_metadata(
        self, df: Union[pd.DataFrame, pd.Series]
    ) -> Dict[str, "MetadataType"]:
        """Extract metadata from the given pandas dataframe or series.

        Args:
            df: The pandas dataframe or series to extract metadata from.

        Returns:
            The extracted metadata as a dictionary.
        """
        pandas_metadata: Dict[str, "MetadataType"] = {"shape": df.shape}

        if isinstance(df, pd.Series):
            pandas_metadata["dtype"] = DType(df.dtype.type)
            pandas_metadata["mean"] = float(df.mean().item())
            pandas_metadata["std"] = float(df.std().item())
            pandas_metadata["min"] = float(df.min().item())
            pandas_metadata["max"] = float(df.max().item())

        else:
            pandas_metadata["dtype"] = {
                str(key): DType(value.type) for key, value in df.dtypes.items()
            }
            for stat_name, stat in {
                "mean": df.mean,
                "std": df.std,
                "min": df.min,
                "max": df.max,
            }.items():
                pandas_metadata[stat_name] = {
                    str(key): float(value)
                    for key, value in stat(numeric_only=True).to_dict().items()
                }

        return pandas_metadata
