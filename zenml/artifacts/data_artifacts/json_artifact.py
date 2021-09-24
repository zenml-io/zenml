#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.

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
