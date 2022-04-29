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
from pathlib import Path
from typing import ClassVar, Union

from ml_metadata.proto import metadata_store_pb2
from pydantic import validator
from tfx.orchestration import metadata

from zenml.io import utils
from zenml.metadata_stores import BaseMetadataStore


class SQLiteMetadataStore(BaseMetadataStore):
    """SQLite backend for ZenML metadata store."""

    uri: str

    # Class Configuration
    FLAVOR: ClassVar[str] = "sqlite"

    @property
    def local_path(self) -> str:
        """Path to the local directory where the SQLite DB is stored."""
        return str(Path(self.uri).parent)

    def get_tfx_metadata_config(
        self,
    ) -> Union[
        metadata_store_pb2.ConnectionConfig,
        metadata_store_pb2.MetadataStoreClientConfig,
    ]:
        """Return tfx metadata config for sqlite metadata store."""
        return metadata.sqlite_metadata_connection_config(self.uri)

    @validator("uri")
    def ensure_uri_is_local(cls, uri: str) -> str:
        """Ensures that the metadata store uri is local."""
        if utils.is_remote(uri):
            raise ValueError(
                f"Uri '{uri}' specified for SQLiteMetadataStore is not a "
                f"local uri."
            )

        return uri
