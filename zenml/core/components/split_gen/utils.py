#  Copyright (c) maiot GmbH 2020. All Rights Reserved.
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
from typing import List, Text, Dict

import tensorflow_data_validation as tfdv
from tfx import types
from tfx.components.schema_gen.executor import _DEFAULT_FILE_NAME, SCHEMA_KEY
from tfx.types import artifact_utils
from tfx.types.artifact import Artifact
from tfx.utils import io_utils


def parse_statistics(split_name: Text,
                     statistics: List[Artifact]) -> Dict[Text, int]:
    stats_uri = io_utils.get_only_uri_in_dir(
        artifact_utils.get_split_uri(statistics, split_name))

    stats = tfdv.load_statistics(stats_uri)

    return stats


def parse_schema(input_dict: Dict[Text, List[types.Artifact]]):
    schema = input_dict.get(SCHEMA_KEY, None)
    if not schema:
        return schema
    else:
        schema_path = os.path.join(
            artifact_utils.get_single_uri(schema),
            _DEFAULT_FILE_NAME)
        schema_reader = io_utils.SchemaReader()
        parsed_schema = schema_reader.read(schema_path)

        return parsed_schema
