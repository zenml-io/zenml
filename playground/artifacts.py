import pandas as pd

from playground.base_artifact import BaseArtifact


class DataArtifact(BaseArtifact):
    def read(self):
        return pd.read_csv(self.uri)

    def write(self, df: pd.DataFrame):
        df.to_csv(self.uri)
