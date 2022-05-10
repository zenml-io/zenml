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
from typing import ClassVar, Optional, Union

from ml_metadata.proto import metadata_store_pb2
from ml_metadata.proto.metadata_store_pb2 import MySQLDatabaseConfig
from pydantic import root_validator

from zenml.metadata_stores import BaseMetadataStore


class MySQLMetadataStore(BaseMetadataStore):
    """MySQL backend for ZenML metadata store."""

    host: str
    port: int
    database: str
    username: str
    password: str
    ssl_key: Optional[str]
    ssl_cert: Optional[str]
    ssl_ca: Optional[str]

    # Class Configuration
    FLAVOR: ClassVar[str] = "mysql"

    def get_tfx_metadata_config(
        self,
    ) -> Union[
        metadata_store_pb2.ConnectionConfig,
        metadata_store_pb2.MetadataStoreClientConfig,
    ]:
        """Return tfx metadata config for mysql metadata store."""
        if self.ssl_key:
            return metadata_store_pb2.ConnectionConfig(
                mysql=MySQLDatabaseConfig(
                    host=self.host,
                    port=self.port,
                    database=self.database,
                    user=self.username,
                    password=self.password,
                    ssl_options=metadata_store_pb2.MySQLDatabaseConfig.SSLOptions(
                        key=self.ssl_key,
                        cert=self.ssl_cert,
                        ca=self.ssl_ca,
                    ),
                )
            )
        else:
            return metadata_store_pb2.ConnectionConfig(
                MySQLDatabaseConfig(
                    host=self.host,
                    port=self.port,
                    database=self.database,
                    user=self.username,
                    password=self.password,
                )
            )

    @root_validator()
    def ssl_options_have_correct_keys(cls, values):
        required_keys = ["ssl_key", "ssl_cert", "ssl_ca"]
        if any(key in values for key in required_keys):
            if not all(key in values for key in required_keys):
                raise ValueError(
                    f"Missing key(s): "
                    f"{[key not in values for key in required_keys]} "
                    f"in the SSL options of your MySQL Metadata Store."
                )

        return values
