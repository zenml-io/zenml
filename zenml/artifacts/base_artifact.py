from tfx.types import Artifact

from zenml.artifacts.utils import WriterFactory


class BaseArtifact(Artifact):
    """ """

    TYPE_NAME = "BaseArtifact"
    PROPERTIES = {}

    WRITER_FACTORY = WriterFactory()

    def get_writer(self, key):
        return self.WRITER_FACTORY.get_single_type(key)
