#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""Modal-hosted ZenML server + MariaDB test deployment."""

from tests.harness.deployment.base import (
    MARIADB_DOCKER_IMAGE,
    MARIADB_ROOT_PASSWORD,
)
from tests.harness.deployment.server_modal_mysql import (
    ServerModalMySQLTestDeployment,
)
from tests.harness.model import DatabaseType, ServerType


class ServerModalMariaDBTestDeployment(ServerModalMySQLTestDeployment):
    """MariaDB variant of the Modal-hosted test deployment.

    MariaDB's ``docker-entrypoint.sh`` exposes the same
    ``MYSQL_ROOT_PASSWORD`` / ``MYSQL_DATABASE`` env-var contract as
    MySQL, so the shared entrypoint script and store URL format work
    unchanged.
    """

    DB_IMAGE = MARIADB_DOCKER_IMAGE
    DB_ROOT_PASSWORD = MARIADB_ROOT_PASSWORD


ServerModalMariaDBTestDeployment.register_deployment_class(
    server_type=ServerType.MODAL, database_type=DatabaseType.MARIADB
)
