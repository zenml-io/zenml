import os

import pandas as pd

from playground.artifacts.base_artifact import BaseArtifact

# Artifact types
DEFAULT_FILENAME = "data.csv"


class CSVArtifact(BaseArtifact):
    TYPE_NAME = 'csv_artifact'

    def read(self):
        return pd.read_csv(os.path.join(self.uri, DEFAULT_FILENAME))

    def write(self, df: pd.DataFrame):
        df.to_csv(os.path.join(self.uri, DEFAULT_FILENAME))
