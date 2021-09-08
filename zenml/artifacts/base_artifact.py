from tfx.types import Artifact

from zenml.artifacts.utils import WriterFactory


class BaseArtifact(Artifact):
    """ """

    TYPE_NAME = "BaseArtifact"
    PROPERTIES = {}

    WRITERS = WriterFactory()

    def get_writer(self, key):
        return self.WRITERS.get_single_type(key)
