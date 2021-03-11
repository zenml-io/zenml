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

from typing import Text

from tfx.orchestration import metadata

from zenml.metadata import ZenMLMetadataStore
from zenml.utils import path_utils
from zenml.enums import MLMetadataTypes


class SQLiteMetadataStore(ZenMLMetadataStore):
    STORE_TYPE = MLMetadataTypes.sqlite.name

    def __init__(self, uri: Text):
        """Constructor for MySQL MetadataStore for ZenML"""
        if path_utils.is_remote(uri):
            raise Exception(f'URI {uri} is a non-local path. A sqlite store '
                            f'can only be local paths')

        # Resolve URI if relative URI provided
        self.uri = path_utils.resolve_relative_path(uri)
        super().__init__()

    def get_tfx_metadata_config(self):
        return metadata.sqlite_metadata_connection_config(self.uri)
