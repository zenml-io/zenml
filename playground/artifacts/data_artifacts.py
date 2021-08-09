import os
from abc import abstractmethod

import pandas as pd

from playground.artifacts.base_artifact import BaseArtifact

# Artifact types
DEFAULT_FILENAME = "data.csv"


class BaseDataArtifact(BaseArtifact):
    TYPE_NAME = "data_artifact"
    PROPERTIES = {

    }

    @abstractmethod
    def read(self):
        pass

    @abstractmethod
    def write(self, df: pd.DataFrame):
        pass


class CSVArtifact(BaseDataArtifact):
    TYPE_NAME = 'csv_artifact'

    def read(self):
        return pd.read_csv(os.path.join(self.uri, DEFAULT_FILENAME))

    def write(self, df: pd.DataFrame):
        df.to_csv(os.path.join(self.uri, DEFAULT_FILENAME))
