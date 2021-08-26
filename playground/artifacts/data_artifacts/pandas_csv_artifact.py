import os

import pandas as pd

from playground.artifacts.data_artifacts.base_data_artifact import \
    BaseDataArtifact, DEFAULT_FILENAME


class PandasCSVArtifact(BaseDataArtifact):
    TYPE_NAME = "csv_data_artifact"

    def read(self):
        return pd.read_csv(os.path.join(self.uri, DEFAULT_FILENAME))

    def write(self, df: pd.DataFrame):
        df.to_csv(os.path.join(self.uri, DEFAULT_FILENAME))
