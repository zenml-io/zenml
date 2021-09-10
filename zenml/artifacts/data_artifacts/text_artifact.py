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


def write_with_beam(artifact, pipeline):
    """

    Args:
      artifact:
      pipeline:

    Returns:

    """
    import apache_beam as beam

    out_path = os.path.join(artifact.uri, DEFAULT_FILENAME)
    return pipeline | beam.io.WriteToText(out_path)


class TextArtifact(BaseDataArtifact):
    """ """

    TYPE_NAME = "text_artifact"

    WRITER_FACTORY = WriterFactory()
    WRITER_FACTORY.register_type(PandasOutput, write_with_pandas)
    WRITER_FACTORY.register_type(BeamOutput, write_with_beam)

    def read_with_pandas(self):
        """ """
        import pandas as pd

        return pd.read_csv(os.path.join(self.uri, DEFAULT_FILENAME))

    def read_with_beam(self, pipeline):
        """

        Args:
          pipeline:

        Returns:

        """
        import apache_beam as beam
        from tfx.dsl.io import fileio

        if fileio.isdir(self.uri):
            txt_files = fileio.listdir(self.uri)
        else:
            if fileio.exists(self.uri):
                txt_files = [self.uri]
            else:
                raise RuntimeError(f"{self.uri} does not exist.")

        txt_files = [os.path.join(self.uri, file) for file in txt_files]

        return (pipeline
                | "ReadText" >> beam.io.ReadFromText(file_pattern=txt_files[0],
                                                     skip_header_lines=1)
                | "ParsedLines" >> beam.Map(parse_line))
