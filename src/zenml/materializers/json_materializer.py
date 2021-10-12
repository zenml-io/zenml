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
from typing import Union

from zenml.materializers.base_materializer import BaseMaterializer
from zenml.utils import yaml_utils

DEFAULT_FILENAME = "data.json"


# TODO [MEDIUM]: Make this more extensive.
class JsonMaterializer(BaseMaterializer):
    """Read/Write JSON files."""

    ASSOCIATED_TYPES = [int, str, bytes, dict, float, list, tuple]

    def handle_input(self) -> dict:
        """TBD"""
        filepath = os.path.join(self.artifact.uri, DEFAULT_FILENAME)
        return yaml_utils.read_json(filepath)

    def handle_return(
        self, data: Union[int, str, bytes, dict, float, list, tuple]
    ):
        """TBD"""
        filepath = os.path.join(self.artifact.uri, DEFAULT_FILENAME)
        yaml_utils.write_json(filepath, data)
