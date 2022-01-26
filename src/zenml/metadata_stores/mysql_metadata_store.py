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
from typing import Union

from ml_metadata.proto import metadata_store_pb2
from tfx.orchestration import metadata

from zenml.enums import MetadataStoreFlavor
from zenml.metadata_stores import BaseMetadataStore


class MySQLMetadataStore(BaseMetadataStore):
    """MySQL backend for ZenML metadata store."""

    host: str
    port: int
    database: str
    username: str
    password: str
    supports_local_execution = True
    supports_remote_execution = True

    @property
    def flavor(self) -> MetadataStoreFlavor:
        """The metadata store flavor."""
        return MetadataStoreFlavor.MYSQL

    def get_tfx_metadata_config(
        self,
    ) -> Union[
        metadata_store_pb2.ConnectionConfig,
        metadata_store_pb2.MetadataStoreClientConfig,
    ]:
        """Return tfx metadata config for mysql metadata store."""
        return metadata.mysql_metadata_connection_config(
            host=self.host,
            port=self.port,
            database=self.database,
            username=self.username,
            password=self.password,
        )
