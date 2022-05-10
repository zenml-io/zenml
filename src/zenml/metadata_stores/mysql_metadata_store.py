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
from typing import ClassVar, Union, Any

from ml_metadata.proto import metadata_store_pb2
from ml_metadata.proto.metadata_store_pb2 import MySQLDatabaseConfig

from zenml.metadata_stores import BaseMetadataStore
from zenml.repository import Repository
import os

SSL_KEYS = ['ssl_key', 'ssl_ca', 'ssl_cert']
BASE_PATH = os.getcwd()


class MySQLMetadataStore(BaseMetadataStore):
    """MySQL backend for ZenML metadata store."""

    host: str
    port: int
    database: str

    secret: str

    # Class Configuration
    FLAVOR: ClassVar[str] = "mysql"

    def get_tfx_metadata_config(
        self,
    ) -> Union[
        metadata_store_pb2.ConnectionConfig,
        metadata_store_pb2.MetadataStoreClientConfig,
    ]:
        """Return tfx metadata config for mysql metadata store."""

        secret = self._obtain_mysql_secret()

        config = MySQLDatabaseConfig(
            host=self.host,
            port=self.port,
            database=self.database,
            user=secret.user,
        )

        if secret.password:
            config.password = secret.password

        if any(getattr(secret, key) is not None for key in SSL_KEYS):
            if not all(getattr(secret, key) is not None for key in SSL_KEYS):
                raise RuntimeError(
                    f"Missing ssl keys in secret: "
                    f"{[key for key in SSL_KEYS if key not in secret]}"
                )

            ssl_options = {}
            for key in SSL_KEYS:
                content = getattr(secret, key)
                filepath = os.path.join(BASE_PATH, f"{key}.pem")
                ssl_options[key] = filepath
                with open(filepath, 'w') as f:
                    f.write(content)

            ssl_options = MySQLDatabaseConfig.SSLOptions(
                cert=ssl_options["ssl_cert"],
                ca=ssl_options["ssl_ca"],
                key=ssl_options["ssl_key"],
            )
            config.ssl_options.CopyFrom(ssl_options)

        return metadata_store_pb2.ConnectionConfig(mysql=config)

    def _obtain_mysql_secret(self) -> Any:
        secret_manager = Repository().active_stack.secrets_manager

        if not secret_manager:
            raise RuntimeError("You dont have the secret manager")  # TODO

        try:
            mysql_secret = secret_manager.get_secret(self.secret)
        except KeyError:
            raise RuntimeError("You dont have the right key")

        # if isinstance(mysql_secret, MySQLSchema):
        #     raise RuntimeError("You dont have the right secret schema.")

        return mysql_secret
