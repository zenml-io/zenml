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
from typing import Any, ClassVar, Optional, Union

from ml_metadata.proto import metadata_store_pb2
from ml_metadata.proto.metadata_store_pb2 import MySQLDatabaseConfig

from zenml.config.global_config import GlobalConfiguration
from zenml.io import fileio
from zenml.metadata_stores import BaseMetadataStore
from zenml.repository import Repository


class MySQLMetadataStore(BaseMetadataStore):
    """MySQL backend for ZenML metadata store."""

    username: Optional[str]
    password: Optional[str]
    host: str
    port: int
    database: str

    secret: Optional[str]

    # Class Configuration
    FLAVOR: ClassVar[str] = "mysql"

    def get_tfx_metadata_config(
        self,
    ) -> Union[
        metadata_store_pb2.ConnectionConfig,
        metadata_store_pb2.MetadataStoreClientConfig,
    ]:
        """Return tfx metadata config for MySQL metadata store."""
        config = MySQLDatabaseConfig(
            host=self.host,
            port=self.port,
            database=self.database,
        )

        secret = self._get_mysql_secret()

        # Set the user
        if self.username:
            if secret and secret.user:
                raise RuntimeError(
                    f"Both the metadata store {self.name} and the secret "
                    f"{self.secret} within your secrets manager define "
                    f"a username `{self.username}` and `{secret.user}`. Please "
                    f"make sure that you only use one."
                )
            else:
                config.user = self.username
        else:
            if secret and secret.user:
                config.user = secret.user
            else:
                raise RuntimeError(
                    "Your metadata store does not have a username. Please "
                    "provide it either by defining it upon registration or "
                    "through a MySQL secret."
                )

        # Set the password
        if self.password:
            if secret and secret.password:
                raise RuntimeError(
                    f"Both the metadata store {self.name} and the secret "
                    f"{self.secret} within your secrets manager define "
                    f"a password. Please make sure that you only use one."
                )
            else:
                config.password = self.password
        else:
            if secret and secret.password:
                config.password = secret.password

        # Set the SSL configuration if there is one
        if secret:
            secret_folder = Path(
                GlobalConfiguration().config_directory,
                "mysql-metadata",
                str(self.uuid),
            )

            ssl_options = {}
            # Handle the files
            for key in ["ssl_key", "ssl_ca", "ssl_cert"]:
                content = getattr(secret, key)
                if content:
                    fileio.makedirs(str(secret_folder))
                    file_path = Path(secret_folder, f"{key}.pem")
                    ssl_options[key.lstrip("ssl_")] = str(file_path)
                    with open(file_path, "w") as f:
                        f.write(content)
                    file_path.chmod(0o600)

            # Handle additional params
            ssl_options["verify_server_cert"] = secret.ssl_verify_server_cert

            ssl_options = MySQLDatabaseConfig.SSLOptions(**ssl_options)
            config.ssl_options.CopyFrom(ssl_options)

        return metadata_store_pb2.ConnectionConfig(mysql=config)

    def _get_mysql_secret(self) -> Any:
        """Method which returns a MySQL secret from the secrets manager."""
        if self.secret:
            active_stack = Repository().active_stack
            secret_manager = active_stack.secrets_manager
            if secret_manager is None:
                raise RuntimeError(
                    f"The metadata store `{self.name}` that you are using "
                    f"requires a secret. However, your stack "
                    f"`{active_stack.name}` does not have a secrets manager."
                )
            try:
                secret = secret_manager.get_secret(self.secret)

                from zenml.metadata_stores.mysql_secret_schema import (
                    MYSQLSecretSchema,
                )

                if not isinstance(secret, MYSQLSecretSchema):
                    raise RuntimeError(
                        f"If you are using a secret with a MySQL Metadata "
                        f"Store, please make sure to use the schema: "
                        f"{MYSQLSecretSchema.TYPE}"
                    )
                return secret

            except KeyError:
                raise RuntimeError(
                    f"The secret `{self.secret}` used for your MySQL metadata "
                    f"store `{self.name}` does not exist in your secrets "
                    f"manager `{secret_manager.name}`."
                )
        return None
