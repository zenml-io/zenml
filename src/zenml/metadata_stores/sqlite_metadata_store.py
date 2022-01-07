#  Copyright (c) ZenML GmbH 2020. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
from typing import Any

from ml_metadata.proto import metadata_store_pb2
from pydantic import validator
from tfx.orchestration import metadata

from zenml.io import fileio
from zenml.metadata_stores import BaseMetadataStore


class SQLiteMetadataStore(BaseMetadataStore):
    """SQLite backend for ZenML metadata store."""

    uri: str

    def __init__(self, **data: Any):
        """Constructor for MySQL MetadataStore for ZenML."""
        super().__init__(**data)

        # TODO [ENG-131]: Replace with proper custom validator.
        if fileio.is_remote(self.uri):
            raise Exception(
                f"URI {self.uri} is a non-local path. A sqlite store "
                f"can only be local paths"
            )

        # Resolve URI if relative URI provided
        # self.uri = fileio.resolve_relative_path(uri)

    def get_tfx_metadata_config(self) -> metadata_store_pb2.ConnectionConfig:
        """Return tfx metadata config for sqlite metadata store."""
        return metadata.sqlite_metadata_connection_config(self.uri)

    @validator("uri")
    def uri_must_be_local(cls, v: str) -> str:
        """Validator to ensure uri is local"""
        if fileio.is_remote(v):
            raise ValueError(
                f"URI {v} is a non-local path. A sqlite store "
                f"can only be local paths"
            )
        return v
