import json
import os

from zenml.annotations.artifact_annotations import JSONOutput
from zenml.artifacts.data_artifacts.base_data_artifact import BaseDataArtifact
from zenml.artifacts.utils import WriterFactory

DEFAULT_FILENAME = "data.json"


def write_with_json(artifact, data):
    """ """

    file = open(os.path.join(artifact.uri, DEFAULT_FILENAME), "w")
    json.dump(data, file)


class JSONArtifact(BaseDataArtifact):
    """ """

    TYPE_NAME = "primitive_artifact"

    WRITER_FACTORY = WriterFactory()
    WRITER_FACTORY.register_type(JSONOutput, write_with_json)

    def read_with_json(self):
        """ """

        file = open(os.path.join(self.uri, DEFAULT_FILENAME), "r")
        return json.load(file)
