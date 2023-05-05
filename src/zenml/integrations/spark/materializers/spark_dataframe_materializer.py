#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""Implementation of the Spark Dataframe Materializer."""

import os.path
from typing import Any, ClassVar, Dict, Tuple, Type

from pyspark.sql import DataFrame, SparkSession

from zenml.enums import ArtifactType
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.metadata.metadata_types import MetadataType

DEFAULT_FILEPATH = "data"


class SparkDataFrameMaterializer(BaseMaterializer):
    """Materializer to read/write Spark dataframes."""

    ASSOCIATED_TYPES: ClassVar[Tuple[Type[Any], ...]] = (DataFrame,)
    ASSOCIATED_ARTIFACT_TYPE: ClassVar[ArtifactType] = ArtifactType.DATA

    def load(self, data_type: Type[Any]) -> DataFrame:
        """Reads and returns a spark dataframe.

        Args:
            data_type: The type of the data to read.

        Returns:
            A loaded spark dataframe.
        """
        # Create the Spark session
        spark = SparkSession.builder.getOrCreate()

        # Read the data
        path = os.path.join(self.uri, DEFAULT_FILEPATH)
        return spark.read.parquet(path)

    def save(self, df: DataFrame) -> None:
        """Writes a spark dataframe.

        Args:
            df: A spark dataframe object.
        """
        # Write the dataframe to the artifact store
        path = os.path.join(self.uri, DEFAULT_FILEPATH)
        df.write.parquet(path)

    def extract_metadata(self, df: DataFrame) -> Dict[str, "MetadataType"]:
        """Extract metadata from the given `DataFrame` object.

        Args:
            df: The `DataFrame` object to extract metadata from.

        Returns:
            The extracted metadata as a dictionary.
        """
        return {
            "shape": (df.count(), len(df.columns)),
        }
