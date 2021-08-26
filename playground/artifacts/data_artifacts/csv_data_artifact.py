import os
import pandas as pd
from playground.artifacts.data_artifacts.base_data_artifact import \
    BaseDataArtifact
import apache_beam as beam

# Artifact types
DEFAULT_FILENAME = "data.csv"


class PandasCSVArtifact(BaseDataArtifact):
    TYPE_NAME = "csv_data_artifact"

    def read(self):
        return pd.read_csv(os.path.join(self.uri, DEFAULT_FILENAME))

    def write(self, df: pd.DataFrame):
        df.to_csv(os.path.join(self.uri, DEFAULT_FILENAME))


class BeamCSVArtifact(BaseDataArtifact):
    TYPE_NAME = "beam_data_artifact"

    def read(self, pipeline):
        file_pattern = os.path.join(self.uri, "*")

        # if path_utils.is_dir(self.path):
        #     csv_files = path_utils.list_dir(self.path)
        #     if not csv_files:
        #         raise RuntimeError(
        #             'Split pattern {} does not match any files.'.format(
        #                 file_pattern))
        # else:
        #     if path_utils.file_exists(self.path):
        #         csv_files = [self.path]
        #     else:
        #         raise RuntimeError(f'{self.path} does not exist.')

        # weed out bad file exts with this logic
        allowed_file_exts = [".csv", ".txt"]  # ".dat"
        csv_files = [uri for uri in csv_files if os.path.splitext(uri)[1]
                     in allowed_file_exts]

        # Always use header from file
        column_names = path_utils.load_csv_header(csv_files[0])

        return (pipeline | 'ReadFromText' >> beam.io.ReadFromText(file_pattern=self.path, skip_header_lines=1)
                | 'ParseCSVLine' >> beam.ParDo(csv_decoder.ParseCSVLine(delimiter=','))
                | 'ExtractParsedCSVLines' >> beam.Map(lambda x: dict(zip(column_names, x[0]))))

    def write(self):
