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

from zenml.materializers.base_materializer import BaseMaterializer
from zenml.utils import yaml_utils

DEFAULT_FILENAME = "data.json"


class JsonMaterializer(BaseMaterializer):
    """Read data to and from JSON."""

    TYPE_NAME = "json"

    def read_file(self, filename=None):
        """Read JSON from filename."""
        filepath = os.path.join(
            self.artifact.uri,
            filename if filename is not None else DEFAULT_FILENAME,
        )
        return yaml_utils.read_json(filepath)

    def write_file(self, data, filename=None):
        """Write JSON to filename."""
        filepath = os.path.join(
            self.artifact.uri,
            filename if filename is not None else DEFAULT_FILENAME,
        )

        yaml_utils.write_json(filepath, data)
