#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.

import os
from typing import Type

import pandas as pd

from zenml.materializers.base_materializer import BaseMaterializer

DEFAULT_FILENAME = "df.parquet.gzip"
COMPRESSION_TYPE = "gzip"


class PandasMaterializer(BaseMaterializer):
    """Materializer to read data to and from pandas."""

    ASSOCIATED_TYPES = [pd.DataFrame]

    def handle_input(self, data_type: Type) -> pd.DataFrame:
        """Reads pd.Dataframe from a parquet file."""
        super().handle_input(data_type)
        return pd.read_parquet(
            os.path.join(self.artifact.uri, DEFAULT_FILENAME)
        )

    def handle_return(self, df: pd.DataFrame):
        """Writes a pandas dataframe to the specified filename.

        Args:
            df: The pandas dataframe to write.
        """
        super().handle_return(df)
        filepath = os.path.join(self.artifact.uri, DEFAULT_FILENAME)
        df.to_parquet(filepath, compression=COMPRESSION_TYPE)
