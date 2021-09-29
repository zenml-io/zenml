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

# TODO: [LOW] Revise the docstrings

from zenml.artifacts.data_artifacts.base_data_artifact import BaseDataArtifact

DEFAULT_FILENAME = "data.txt"


class TextArtifact(BaseDataArtifact):
    """ZenML text-based artifact"""

    TYPE_NAME = "text_artifact"

    # READERS #################################################################

    def read_with_pandas(self):
        """reader function to read the artifact with pandas

        Returns:
            a pandas.DataFrame
        """
        import os

        import pandas as pd

        return pd.read_csv(os.path.join(self.uri, DEFAULT_FILENAME))

    def read_with_beam(self, pipeline):
        """reader function to read the artifact with apache-beam

        It appends a step to the given pipeline to read the data

        Args:
            pipeline: a beam.Pipeline instance

        Returns:
            the new pipeline with the appended read steps
        """
        import os

        import apache_beam as beam

        return pipeline | "ReadText" >> beam.io.ReadFromText(
            file_pattern=os.path.join(self.uri, "*")
        )

    # WRITERS #################################################################

    def write_with_pandas(self, df):
        """writer function to write a text artifact with pandas

        Args:
          df: the pandas.DataFrame which needs to be written to the artifact
        """
        import os

        df.to_csv(os.path.join(self.uri, DEFAULT_FILENAME))

    def write_with_beam(self, pipeline):
        """writer function to write a text artifact with apache-beam

        It appends a step to the given pipeline to write the data

        Args:
          pipeline: a beam.Pipeline instance

        Returns:
            the new pipeline with the appended write steps
        """
        import os

        import apache_beam as beam

        return pipeline | beam.io.WriteToText(
            os.path.join(self.uri, DEFAULT_FILENAME)
        )
