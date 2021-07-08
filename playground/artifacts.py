import pandas as pd
from tfx.dsl.component.experimental.annotations import InputArtifact, \
    OutputArtifact, Parameter

from playground.base_artifact import BaseArtifact


# Input and output wrappers

class Input(InputArtifact):
    pass


class Output(OutputArtifact):
    pass


class Param(Parameter):
    pass


# Artifact types

class DataArtifact(BaseArtifact):
    TYPE_NAME = 'data_artifact'

    def read(self):
        return pd.read_csv(self.uri)

    def write(self, df: pd.DataFrame):
        df.to_csv(self.uri)
