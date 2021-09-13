import os

from zenml.annotations.artifact_annotations import PandasOutput
from zenml.artifacts.data_artifacts.base_data_artifact import BaseDataArtifact
from zenml.artifacts.utils import WriterFactory

DEFAULT_FILENAME = "data.csv"


def write_with_pandas(artifact, df):
    """ """
    df.to_csv(os.path.join(artifact.uri, DEFAULT_FILENAME))


class PandasArtifact(BaseDataArtifact):
    """ """

    TYPE_NAME = "pandas_artifact"

    WRITER_FACTORY = WriterFactory()
    WRITER_FACTORY.register_type(PandasOutput, write_with_pandas)

    def read_with_pandas(self):
        """ """
        import pandas as pd
        return pd.read_csv(os.path.join(self.uri, DEFAULT_FILENAME))
