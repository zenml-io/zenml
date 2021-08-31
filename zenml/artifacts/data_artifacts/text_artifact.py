import os

from zenml.artifacts.data_artifacts.base import BaseDataArtifact

DEFAULT_FILENAME = "data.txt"


def parse_line(x):
    return x


class TextArtifact(BaseDataArtifact):
    TYPE_NAME = "text_artifact"

    def read_with_beam(self, pipeline):

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

        return (
            pipeline
            | "ReadText"
            >> beam.io.ReadFromText(
                file_pattern=txt_files[0],
                # TODO: testing first file
                skip_header_lines=1,
            )
            | "ParsedLines" >> beam.Map(parse_line)
        )

    def write_with_beam(self, pipeline):
        import apache_beam as beam

        out_path = os.path.join(self.uri, DEFAULT_FILENAME)
        return pipeline | beam.io.WriteToText(out_path)

    def read_with_pandas(self):
        import pandas as pd

        return pd.read_csv(os.path.join(self.uri, DEFAULT_FILENAME))

    def write_with_pandas(self, df):
        df.to_csv(os.path.join(self.uri, DEFAULT_FILENAME))
