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

import tempfile
from typing import Any, Type

from pyspark.sql import DataFrame, SparkSession

from zenml.io import fileio
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.utils import io_utils


class SparkDataFrameMaterializer(BaseMaterializer):
    """Materializer to read/write NeuralProphet models."""

    ASSOCIATED_TYPES = (DataFrame,)

    def handle_input(self, data_type: Type[Any]) -> DataFrame:
        """Reads and returns a spark dataframe.
        Returns:
            A loaded spark dataframe.
        """
        super().handle_input(data_type)

        # Create a temporary directory to store the dataframe
        temp_dir = tempfile.TemporaryDirectory()

        # Copy from the dataframe to temporary directory
        io_utils.copy_dir(self.artifact.uri, temp_dir.name)

        # Create the Spark Session
        spark = SparkSession.builder.getOrCreate()

        # Read the data from the temporary directory
        return spark.read.load(temp_dir.name, format="parquet")

    def handle_return(self, df: DataFrame) -> None:
        """Writes a spark dataframe.
        Args:
            df: A spark dataframe object.
        """
        # Create a temporary directory to store the model
        temp_dir = tempfile.TemporaryDirectory()

        super().handle_return(df)
        df.write.save(temp_dir.name, format="parquet")

        io_utils.copy_dir(temp_dir.name, self.artifact.uri)

        # Remove the temporary directory
        fileio.rmtree(temp_dir.name)
