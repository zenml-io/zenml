#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""Functionality to support ZenML store configurations."""

import re
from typing import Any, Dict, Optional, Tuple, Union

from pydantic import BaseModel, ConfigDict, SerializeAsAny, model_validator
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError
from sqlalchemy.util import immutabledict

from zenml.config.secrets_store_config import SecretsStoreConfiguration
from zenml.constants import (
    is_false_string_value,
    is_true_string_value,
)
from zenml.enums import SQLDatabaseDriver, StoreType
from zenml.logger import get_logger
from zenml.utils.networking_utils import (
    replace_localhost_with_internal_hostname,
)
from zenml.utils.pydantic_utils import before_validator_handler
from zenml.utils.secret_utils import PlainSerializedSecretStr

logger = get_logger(__name__)


class StoreConfiguration(BaseModel):
    """Generic store configuration.

    The store configurations of concrete store implementations must inherit from
    this class and validate any extra attributes that are configured in addition
    to those defined in this class.

    Attributes:
        type: The type of store backend.
        url: The URL of the store backend.
        secrets_store: The configuration of the secrets store to use to store
            secrets. If not set, secrets management is disabled.
        backup_secrets_store: The configuration of the secrets store to use to
            store backups of secrets. If not set, backup and restore of secrets
            are disabled.
    """

    type: StoreType
    url: str
    secrets_store: Optional[SerializeAsAny[SecretsStoreConfiguration]] = None
    backup_secrets_store: Optional[
        SerializeAsAny[SecretsStoreConfiguration]
    ] = None

    @classmethod
    def supports_url_scheme(cls, url: str) -> bool:
        """Check if a URL scheme is supported by this store.

        Concrete store configuration classes should override this method to
        check if a URL scheme is supported by the store.

        Args:
            url: The URL to check.

        Returns:
            True if the URL scheme is supported, False otherwise.
        """
        return True

    @model_validator(mode="before")
    @classmethod
    @before_validator_handler
    def validate_store_config(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate the secrets store configuration.

        Args:
            data: The values of the store configuration.

        Returns:
            The values of the store configuration.
        """
        if data.get("secrets_store") is None:
            return data

        # Remove the legacy REST secrets store configuration since it is no
        # longer supported/needed
        secrets_store = data["secrets_store"]
        if isinstance(secrets_store, dict):
            secrets_store_type = secrets_store.get("type")
            if secrets_store_type == "rest":
                del data["secrets_store"]

        return data

    @model_validator(mode="after")
    def validate_url(self) -> "StoreConfiguration":
        """Validates the URL for different store types.

        In case of MySQL SQL store, the validator also moves the username,
        password and database parameters from the URL into the other configuration
        arguments, if they are present in the URL.

        Returns:
            The model attribute values.

        Raises:
            ValueError: If the URL is invalid or the SQL driver is not
                supported.
        """
        if self.type == StoreType.SQL:
            # When running inside a container, if the URL uses localhost, the
            # target service will not be available. We try to replace localhost
            # with one of the special Docker or K3D internal hostnames.
            url = replace_localhost_with_internal_hostname(self.url)

            try:
                sql_url = make_url(url)
            except ArgumentError as e:
                raise ValueError(
                    "Invalid SQL URL `%s`: %s. The URL must be in the format "
                    "`driver://[[username:password@]hostname:port]/database["
                    "?<extra-args>]`.",
                    url,
                    str(e),
                )
            if sql_url.drivername not in SQLDatabaseDriver.values():
                raise ValueError(
                    "Invalid SQL driver value `%s`: The driver must be one of: %s.",
                    url,
                    ", ".join(SQLDatabaseDriver.values()),
                )
            self.driver: Optional[SQLDatabaseDriver] = SQLDatabaseDriver(
                sql_url.drivername
            )

            if sql_url.drivername == SQLDatabaseDriver.SQLITE:
                if (
                    sql_url.username
                    or sql_url.password
                    or sql_url.query
                    or sql_url.database is None
                ):
                    raise ValueError(
                        "Invalid SQLite URL `%s`: The URL must be in the "
                        "format `sqlite:///path/to/database.db`.",
                        url,
                    )
                if getattr(self, "username", None) or getattr(
                    self, "password", None
                ):
                    raise ValueError(
                        "Invalid SQLite configuration: The username and password "
                        "must not be set",
                        url,
                    )
                self.database: Optional[str] = sql_url.database
            elif sql_url.drivername == SQLDatabaseDriver.MYSQL:
                if sql_url.username:
                    self.username: Optional[PlainSerializedSecretStr] = (
                        PlainSerializedSecretStr(sql_url.username)
                    )
                    sql_url = sql_url._replace(username=None)
                if sql_url.password:
                    self.password: Optional[PlainSerializedSecretStr] = (
                        PlainSerializedSecretStr(sql_url.password)
                    )
                    sql_url = sql_url._replace(password=None)
                if sql_url.database:
                    self.database = sql_url.database
                    sql_url = sql_url._replace(database=None)
                if sql_url.query:

                    def _get_query_result(
                        result: Union[str, Tuple[str, ...]],
                    ) -> Optional[str]:
                        """Returns the only or the first result of a query.

                        Args:
                            result: The result of the query.

                        Returns:
                            The only or the first result, None otherwise.
                        """
                        if isinstance(result, str):
                            return result
                        elif isinstance(result, tuple) and len(result) > 0:
                            return result[0]
                        else:
                            return None

                    for k, v in sql_url.query.items():
                        if k == "ssl":
                            if r := _get_query_result(v):
                                self.ssl = is_true_string_value(r)
                        elif k == "ssl_ca":
                            if r := _get_query_result(v):
                                self.ssl_ca: Optional[
                                    PlainSerializedSecretStr
                                ] = PlainSerializedSecretStr(r)
                                self.ssl = True
                        elif k == "ssl_cert":
                            if r := _get_query_result(v):
                                self.ssl_cert: Optional[
                                    PlainSerializedSecretStr
                                ] = PlainSerializedSecretStr(r)
                                self.ssl = True
                        elif k == "ssl_key":
                            if r := _get_query_result(v):
                                self.ssl_key: Optional[
                                    PlainSerializedSecretStr
                                ] = PlainSerializedSecretStr(r)
                                self.ssl = True
                        elif k == "ssl_verify_server_cert":
                            if r := _get_query_result(v):
                                if is_true_string_value(r):
                                    self.ssl_verify_server_cert = True
                                elif is_false_string_value(r):
                                    self.ssl_verify_server_cert = False
                        else:
                            raise ValueError(
                                "Invalid MySQL URL query parameter `%s`: The "
                                "parameter must be one of: ssl, ssl_ca, ssl_cert, "
                                "ssl_key, or ssl_verify_server_cert.",
                                k,
                            )
                    sql_url = sql_url._replace(query=immutabledict())

                database = self.database
                if not self.username or not self.password or not database:
                    raise ValueError(
                        "Invalid MySQL configuration: The username, password and "
                        "database must be set in the URL or as configuration "
                        "attributes",
                    )

                regexp = r"^[^\\/?%*:|\"<>.-]{1,64}$"
                match = re.match(regexp, database)
                if not match:
                    raise ValueError(
                        f"The database name does not conform to the required "
                        f"format "
                        f"rules ({regexp}): {database}"
                    )

            return self
        elif self.type == StoreType.REST:
            url = self.url.rstrip("/")
            scheme = re.search("^([a-z0-9]+://)", url)
            if scheme is None or scheme.group() not in ("https://", "http://"):
                raise ValueError(
                    "Invalid URL for REST store: {url}. Should be in the form "
                    "https://hostname[:port] or http://hostname[:port]."
                )

            # When running inside a container, if the URL uses localhost, the
            # target service will not be available. We try to replace localhost
            # with one of the special Docker or K3D internal hostnames.
            self.url = replace_localhost_with_internal_hostname(url)
            return self
        else:
            raise ValueError("Invalid store type: %s" % self.type)

    model_config = ConfigDict(
        # Validate attributes when assigning them. We need to set this in order
        # to have a mix of mutable and immutable attributes
        validate_assignment=True,
        # Allow extra attributes to be set in the base class. The concrete
        # classes are responsible for validating the attributes.
        extra="allow",
    )
