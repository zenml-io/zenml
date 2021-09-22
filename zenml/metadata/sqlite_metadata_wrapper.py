#  Copyright (c) ZenML GmbH 2020. All Rights Reserved.
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
import os.path
from typing import Any, Optional, Text

from pydantic import Field
from tfx.orchestration import metadata

from zenml.enums import MLMetadataTypes
from zenml.metadata.base_metadata_store import BaseMetadataStore
from zenml.utils import path_utils
from zenml.utils.path_utils import get_zenml_config_dir


class SQLiteMetadataStore(BaseMetadataStore):
    """SQLite backend for ZenML metadata store."""

    store_type: Optional[Text] = Field(default=MLMetadataTypes.sqlite)
    uri: Optional[Text] = Field(
        default=os.path.join(get_zenml_config_dir(), "metadata.db")
    )

    def __init__(self, **data: Any):
        """Constructor for MySQL MetadataStore for ZenML."""
        super().__init__(**data)

        # TODO [LOW]: Replace with proper custom validator.
        if path_utils.is_remote(self.uri):
            raise Exception(
                f"URI {self.uri} is a non-local path. A sqlite store "
                f"can only be local paths"
            )

        # Resolve URI if relative URI provided
        # self.uri = path_utils.resolve_relative_path(uri)

    def get_tfx_metadata_config(self):
        """Return tfx metadata config for sqlite metadata store."""
        return metadata.sqlite_metadata_connection_config(self.uri)
