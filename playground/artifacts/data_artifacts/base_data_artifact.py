from abc import abstractmethod

import pandas as pd
from tfx.types.artifact import Property
from tfx.types.artifact import PropertyType

from playground.artifacts.base_artifact import BaseArtifact

# Artifact types
DEFAULT_FILENAME = "data.csv"

SPLIT_NAMES_PROPERTY = Property(type=PropertyType.STRING)


class BaseDataArtifact(BaseArtifact):
    TYPE_NAME = "data_artifact"
    PROPERTIES = {"split_names": SPLIT_NAMES_PROPERTY}

    @abstractmethod
    def read(self):
        pass

    @abstractmethod
    def write(self, df: pd.DataFrame):
        pass
