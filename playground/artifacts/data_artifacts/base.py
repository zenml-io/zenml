from tfx.types.artifact import Property
from tfx.types.artifact import PropertyType

from playground.artifacts.base import BaseArtifact

SPLIT_NAMES_PROPERTY = Property(type=PropertyType.STRING)


class BaseDataArtifact(BaseArtifact):
    TYPE_NAME = "data_artifact"
    PROPERTIES = {"split_names": SPLIT_NAMES_PROPERTY}
