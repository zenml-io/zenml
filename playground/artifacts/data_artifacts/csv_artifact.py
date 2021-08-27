import os

from playground.artifacts.data_artifacts.base import BaseDataArtifact

DEFAULT_FILENAME = "data_csv"


class CSVArtifact(BaseDataArtifact):
    TYPE_NAME = "csv_artifact"

    def read_with_beam(self, pipeline):

        import apache_beam as beam
        from tfx.dsl.io import fileio

        file_pattern = os.path.join(self.uri, "*")

        if fileio.isdir(self.path):
            csv_files = fileio.listdir(self.path)
            if not csv_files:
                raise RuntimeError('Split pattern {} does not match any '
                                   'files.'.format(file_pattern))
        else:
            if fileio.exists(self.path):
                csv_files = [self.path]
            else:
                raise RuntimeError(f'{self.path} does not exist.')

        allowed_file_extensions = [".csv", ".txt"]
        csv_files = [uri for uri in csv_files
                     if os.path.splitext(uri)[1] in allowed_file_extensions]

        with fileio.open(csv_files[0]) as f:
            column_names = f.readline().strip().split(',')

        return (pipeline
                | 'ReadText' >> beam.io.ReadFromText(file_pattern=self.path,
                                                     skip_header_lines=1)
                | 'ExtractParsedCSVLines' >> beam.Map(lambda x:
                                                      dict(zip(column_names,
                                                               x[0]))))

    def write_with_beam(self):
        pass

    def read_with_pandas(self):
        import pandas as pd
        return pd.read_csv(os.path.join(self.uri, DEFAULT_FILENAME))

    def write_with_pandas(self, df):
        df.to_csv(os.path.join(self.uri, DEFAULT_FILENAME))
