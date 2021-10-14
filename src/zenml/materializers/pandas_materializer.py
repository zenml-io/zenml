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
from zenml.utils import path_utils

DEFAULT_FILENAME = "data.csv"


class PandasMaterializer(BaseMaterializer):
    """Materializer to read data to and from pandas."""

    ASSOCIATED_TYPES = [pd.DataFrame]

    def handle_input(self, data_type: Type) -> pd.DataFrame:
        """Reads all files inside the artifact directory and concatenates
        them to a pandas dataframe."""

        filenames = path_utils.list_dir(self.artifact.uri, only_file_names=True)

        valid_filenames = [
            os.path.join(self.artifact.uri, f)
            for f in filenames
            if DEFAULT_FILENAME in f
        ]

        li = []
        for filename in valid_filenames:
            df = pd.read_csv(filename, index_col=None, header=0)
            li.append(df)
        frame = pd.concat(li, axis=0, ignore_index=True)
        return frame

    def handle_return(self, df: pd.DataFrame):
        """Writes a pandas dataframe to the specified filename.

        Args:
            df: The pandas dataframe to write.
        """
        filepath = os.path.join(self.artifact.uri, DEFAULT_FILENAME)
        df.to_csv(filepath)
