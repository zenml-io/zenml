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
"""Materializer for Pandas.

This materializer handles pandas DataFrame and Series objects.

Special features:
    - Handles pandas DataFrames and Series with various data types
    - Provides helpful error messages for custom data type errors
    - Warns when custom data types are detected that might need additional libraries

Environment Variables:
    ZENML_PANDAS_SAMPLE_ROWS: Controls the number of sample rows to include in
        visualizations. Defaults to 10 if not set.
"""

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

# Default number of sample rows to display in visualizations
DEFAULT_SAMPLE_ROWS = 10

# List of standard pandas/numpy dtype prefixes for type checking
STANDARD_DTYPE_PREFIXES = [
    "int",
    "float",
    "bool",
    "datetime",
    "timedelta",
    "object",
    "category",
    "string",
    "complex",
]


def is_standard_dtype(dtype_str: str) -> bool:
    """Check if a dtype string represents a standard pandas/numpy dtype.

    Args:
        dtype_str: String representation of the dtype

    Returns:
        bool: True if it's a standard dtype, False otherwise
    """
    dtype_str = dtype_str.lower()
    return any(prefix in dtype_str for prefix in STANDARD_DTYPE_PREFIXES)


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
            TypeError: Raised if there is an error when reading parquet files.
            zenml_type_error: If the data type is a custom data type.

        Returns:
            The pandas dataframe or series.
        """
        try:
            # First try normal loading
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
        except TypeError as e:
            # Check for common data type error patterns
            error_str = str(e).lower()
            is_dtype_error = (
                "not understood" in error_str
                or "no type" in error_str
                or "cannot deserialize" in error_str
                or "data type" in error_str
            )

            if is_dtype_error:
                # If the error is due to a custom data type, raise a ZenML TypeError
                # This is to avoid the original error from being swallowed
                # and to provide a more helpful error message
                zenml_type_error = TypeError(
                    "Encountered an error with custom data types. This may be due to "
                    "missing libraries that were used when the data was originally created. "
                    "For example, you might need to install libraries like 'geopandas' for "
                    "GeoPandas data types, 'pandas-gbq' for BigQuery data types, or "
                    "'pyarrow' for Arrow data types. Make sure to import these libraries "
                    "in your step code as well as adding them to your step requirements, "
                    "even if you're not directly using them in your code. Pandas needs "
                    "these libraries to be imported to properly load the custom data types. "
                    "Try installing any packages that were used in previous pipeline steps "
                    "but might not be available in the current environment."
                )
                raise zenml_type_error from e
            # We don't know how to handle this error, so re-raise the original error
            raise e

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

        Creates two visualizations:
        1. A statistical description of the data (using df.describe())
        2. A sample of the data (first N rows controlled by ZENML_PANDAS_SAMPLE_ROWS)

        Note:
            The number of sample rows shown can be controlled with the
            ZENML_PANDAS_SAMPLE_ROWS environment variable.

        Args:
            df: The pandas dataframe or series to visualize.

        Returns:
            A dictionary of visualization URIs and their types.
        """
        visualizations = {}
        describe_uri = os.path.join(self.uri, "describe.csv")
        describe_uri = describe_uri.replace("\\", "/")
        with self.artifact_store.open(describe_uri, mode="wb") as f:
            df.describe().to_csv(f)
        visualizations[describe_uri] = VisualizationType.CSV

        # Get the number of sample rows from environment variable or use default
        sample_rows = int(
            os.environ.get("ZENML_PANDAS_SAMPLE_ROWS", DEFAULT_SAMPLE_ROWS)
        )

        # Add our sample visualization (with configurable number of rows)
        if isinstance(df, pd.Series):
            sample_df = df.head(sample_rows).to_frame()
        else:
            sample_df = df.head(sample_rows)

        sample_uri = os.path.join(self.uri, "sample.csv")
        sample_uri = sample_uri.replace("\\", "/")
        with self.artifact_store.open(sample_uri, mode="wb") as f:
            sample_df.to_csv(f)

        visualizations[sample_uri] = VisualizationType.CSV

        return visualizations

    def extract_metadata(
        self, df: Union[pd.DataFrame, pd.Series]
    ) -> Dict[str, "MetadataType"]:
        """Extract metadata from the given pandas dataframe or series.

        Args:
            df: The pandas dataframe or series to extract metadata from.

        Returns:
            The extracted metadata as a dictionary.
        """
        # Store whether it's a Series for later reference
        is_series = isinstance(df, pd.Series)

        # Store original shape before conversion
        original_shape = df.shape

        # Convert Series to DataFrame for consistent handling of dtypes
        if is_series:
            series_obj = df  # Keep original Series for some calculations
            df = df.to_frame(name="series")

        pandas_metadata: Dict[str, "MetadataType"] = {"shape": original_shape}

        # Add information about custom data types to metadata
        custom_types = {}
        try:
            for col, dtype in df.dtypes.items():
                dtype_str = str(dtype)
                if not is_standard_dtype(dtype_str):
                    col_name = "series" if is_series else str(col)
                    custom_types[col_name] = dtype_str
                    # Try to get module information if available
                    try:
                        module_name = dtype.type.__module__
                        custom_types[f"{col_name}_module"] = module_name
                    except (AttributeError, TypeError):
                        pass

            if custom_types:
                pandas_metadata["custom_types"] = custom_types
        except Exception as e:
            logger.debug(f"Error extracting custom type metadata: {e}")

        if is_series:
            # For Series, use the original series object for statistics
            pandas_metadata["dtype"] = DType(series_obj.dtype.type)
            pandas_metadata["mean"] = float(series_obj.mean().item())
            pandas_metadata["std"] = float(series_obj.std().item())
            pandas_metadata["min"] = float(series_obj.min().item())
            pandas_metadata["max"] = float(series_obj.max().item())

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
