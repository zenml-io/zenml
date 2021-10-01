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

from zenml.materializers.base_materializer import BaseMaterializer

DEFAULT_FILENAME = "data.json"


class JsonMaterializer(BaseMaterializer):
    """
    """

    def read(self, input_artifact, filename=None):
        """ """
        filepath = os.path.join(
            input_artifact.uri,
            filename if filename is not None else DEFAULT_FILENAME
        )
        with open(filepath, 'r') as f:
            return json.load(f)

    def write(self, output_artifact, data, filename=None):
        """ """
        filepath = os.path.join(
            output_artifact.uri,
            filename if filename is not None else DEFAULT_FILENAME
        )

        with open(filepath, 'w') as f:
            json.dump(data, f)
