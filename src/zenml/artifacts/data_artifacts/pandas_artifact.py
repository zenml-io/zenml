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

from zenml.annotations.artifact_annotations import PandasOutput
from zenml.artifacts.data_artifacts.base_data_artifact import BaseDataArtifact
from zenml.artifacts.utils import WriterFactory

DEFAULT_FILENAME = "data.csv"


def write_with_pandas(artifact, df):
    """writer function to write the dataframe to a csv file"""
    df.to_csv(os.path.join(artifact.uri, DEFAULT_FILENAME))


class PandasArtifact(BaseDataArtifact):
    """ZenML Pandas artifact"""

    TYPE_NAME = "pandas_artifact"

    # Registering the corresponding writer functions
    WRITER_FACTORY = WriterFactory()
    WRITER_FACTORY.register_type(PandasOutput, write_with_pandas)

    def read_with_pandas(self):
        """reader function to read the df from a csv at the given filepath"""
        import pandas as pd

        return pd.read_csv(os.path.join(self.uri, DEFAULT_FILENAME))
