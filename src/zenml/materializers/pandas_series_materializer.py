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
import tempfile
from typing import Any, Type

import pandas as pd

from zenml.artifacts import DataArtifact, SchemaArtifact, StatisticsArtifact
from zenml.io import fileio
from zenml.materializers.base_materializer import BaseMaterializer


DEFAULT_FILENAME = "df.parquet.gzip"
COMPRESSION_TYPE = "gzip"


class PandasSeriesMaterializer(BaseMaterializer):
    """Materializer to read data to and from pandas Series."""

    ASSOCIATED_TYPES = (pd.Series,)
    ASSOCIATED_ARTIFACT_TYPES = (
        DataArtifact,
        StatisticsArtifact,
        SchemaArtifact,
    )

    def handle_input(self, data_type: Type[Any]) -> pd.Series:
        """Reads pd.Dataframe from a parquet file and returns as pd.Series."""
        super().handle_input(data_type)
        filepath = os.path.join(self.artifact.uri, DEFAULT_FILENAME)

        # Create a temporary folder
        temp_dir = tempfile.mkdtemp(prefix="zenml-temp-")
        temp_file = os.path.join(str(temp_dir), DEFAULT_FILENAME)

        # Copy from artifact store to temporary file
        fileio.copy(filepath, temp_file)

        # Load the model from the temporary file
        df = pd.read_parquet(temp_file)

        # Cleanup and return
        fileio.rmtree(temp_dir)

        return df[df.columns[0]]

    def handle_return(self, series: pd.Series) -> None:
        """Casts a pandas series to pd.Dataframe and writes to the specified filename.

        Args:
            series: The pandas series to write.
        """
        super().handle_return(series)
        filepath = os.path.join(self.artifact.uri, DEFAULT_FILENAME)

        # Create a temporary file to store the model
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".gzip", delete=False
        ) as f:
            series.to_frame().to_parquet(f.name, compression=COMPRESSION_TYPE)
            fileio.copy(f.name, filepath)

        # Close and remove the temporary file
        f.close()
        fileio.remove(f.name)
