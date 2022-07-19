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
"""Secret schema for MySQL metadata store."""

from typing import ClassVar, Optional

from zenml.secret.base_secret import BaseSecretSchema

MYSQL_METADATA_STORE_SCHEMA_TYPE = "mysql"


class MYSQLSecretSchema(BaseSecretSchema):
    """MySQL secret schema.

    Attributes:
        user: database username
        password: database password
        ssl_ca: certificate authority certificate contents. Required for SSL
            enabled authentication if the CA certificate is not part of the
            certificates shipped by the operating system.
        ssl_cert: client certificate contents. Required for SSL enabled
            authentication if client certificates are used.
        ssl_key: client certificate private key contents. Required for SSL
            enabled if client certificates are used.
        ssl_verify_server_cert: set to verify the identity of the server
            against the provided server certificate.
    """

    TYPE: ClassVar[str] = MYSQL_METADATA_STORE_SCHEMA_TYPE

    user: Optional[str]
    password: Optional[str]
    ssl_ca: Optional[str]
    ssl_cert: Optional[str]
    ssl_key: Optional[str]
    ssl_verify_server_cert: Optional[bool] = False
