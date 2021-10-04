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

import os

import apache_beam as beam

from zenml.materializers.base_materializer import BaseMaterializer

DEFAULT_FILENAME = "data"


class BeamMaterializer(BaseMaterializer):
    """Read to and from Beam artifacts."""

    TYPE_NAME = "beam"

    def read_text(self, pipeline):
        """Read from text"""
        return pipeline | "ReadText" >> beam.io.ReadFromText(
            file_pattern=os.path.join(self.artifact.uri, "*")
        )

    def write_text(self, pipeline, shard_name_template="''"):
        """Write from text"""
        return pipeline | beam.io.WriteToText(
            os.path.join(self.artifact.uri, DEFAULT_FILENAME),
            shard_name_template=shard_name_template,
        )
