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
from typing import Any, Type, Union

import pandas as pd

from zenml.artifacts import DataArtifact, SchemaArtifact, StatisticsArtifact
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.materializers.base_materializer import BaseMaterializer

logger = get_logger(__name__)

DEFAULT_FILENAME = "df.parquet.gzip"
COMPRESSION_TYPE = "gzip"

DATAFRAME_FILENAME = "df.pkl"


class PandasMaterializer(BaseMaterializer):
    """Materializer to read data to and from pandas."""

    ASSOCIATED_TYPES = (pd.DataFrame, pd.Series)
    ASSOCIATED_ARTIFACT_TYPES = (
        DataArtifact,
        StatisticsArtifact,
        SchemaArtifact,
    )

    def handle_input(
        self, data_type: Type[Any]
    ) -> Union[pd.DataFrame, pd.Series]:
        """Reads pd.DataFrame or pd.Series from a pickled file.

        Args:
            data_type: The type of the data to read.

        Raises:
            ImportError: If pyarrow or fastparquet is not installed.

        Returns:
            The pandas dataframe or series.
        """
        super().handle_input(data_type)
        dataframe_file = os.path.join(self.artifact.uri, DATAFRAME_FILENAME)

        if fileio.exists(dataframe_file):
            with fileio.open(dataframe_file, "rb") as f:
                df = pd.read_pickle(f)

        elif fileio.exists(os.path.join(self.artifact.uri, DEFAULT_FILENAME)):
            logger.warning(
                "A legacy artifact was found. "
                "This artifact was created with an older version of "
                "ZenML. You can still use it, but it will be "
                "converted to the new format on the next materialization."
            )
            try:
                import fastparquet  # type: ignore
                import pyarrow  # type: ignore

                with fileio.open(
                    os.path.join(self.artifact.uri, DEFAULT_FILENAME), "rb"
                ) as f:
                    df = pd.read_parquet(f)

            except ImportError:
                raise ImportError(
                    "You have an old version of a `PandasMaterializer` ",
                    "data artifact stored in the artifact store ",
                    "as a `.parquet` file, which requires `pyarrow` and ",
                    "`fastparquet`for reading, You can install `pyarrow` & ",
                    "`fastparquet` by running `pip install pyarrow fastparquet`.",
                )

        # validate the type of the data.
        def is_dataframe_or_series(
            df: Union[pd.DataFrame, pd.Series]
        ) -> Union[pd.DataFrame, pd.Series]:
            if issubclass(data_type, pd.Series):
                # Taking the first column if its a series as the assumption
                # is that there will only be one
                assert len(df.columns) == 1
                df = df[df.columns[0]]
                return df
            else:
                return df

        return is_dataframe_or_series(df)

    def handle_return(self, df: Union[pd.DataFrame, pd.Series]) -> None:
        """Writes a pandas dataframe or series to the specified filename.

        Args:
            df: The pandas dataframe or series to write.
        """
        super().handle_return(df)
        with fileio.open(
            os.path.join(self.artifact.uri, DATAFRAME_FILENAME), "wb"
        ) as f:
            df.to_pickle(f)
