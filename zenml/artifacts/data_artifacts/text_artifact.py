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

from zenml.annotations.artifact_annotations import BeamOutput, PandasOutput
from zenml.artifacts.data_artifacts.base_data_artifact import BaseDataArtifact
from zenml.artifacts.utils import WriterFactory

DEFAULT_FILENAME = "data.txt"


def parse_line(x):
    """

    Args:
      x:

    Returns:

    """
    return x


def write_with_pandas(artifact, df):
    """

    Args:
      artifact:
      df:

    Returns:

    """
    df.to_csv(os.path.join(artifact.uri, DEFAULT_FILENAME))


def write_with_beam(artifact, pcolline):
    """

    Args:
      artifact:
      pcolline:

    Returns:

    """
    import apache_beam as beam

    _ = pcolline[0] | beam.io.WriteToText(
        os.path.join(artifact.uri, DEFAULT_FILENAME),
        num_shards=1,
        shard_name_template="")
    pcolline[1].run()


class TextArtifact(BaseDataArtifact):
    """ """

    TYPE_NAME = "text_artifact"

    WRITER_FACTORY = WriterFactory()
    WRITER_FACTORY.register_type(PandasOutput, write_with_pandas)
    WRITER_FACTORY.register_type(BeamOutput, write_with_beam)

    def read_with_pandas(self):
        """ """
        import pandas as pd

        return pd.read_csv(os.path.join(self.uri,
                                        DEFAULT_FILENAME))

    def read_with_beam(self, pipeline):
        """

        Args:
          pipeline:

        Returns:

        """
        import apache_beam as beam

        return (pipeline
                | "ReadText" >> beam.io.ReadFromText(
                    file_pattern=os.path.join(self.uri, "*"))
                | "ParsedLines" >> beam.Map(parse_line))
