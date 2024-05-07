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
"""ZenML test framework configuration."""

from enum import Enum
from typing import TYPE_CHECKING, Dict, Optional

from pydantic import ConfigDict, Field

from tests.harness.model.base import BaseTestConfigModel
from tests.harness.model.secret import BaseTestSecretConfigModel

if TYPE_CHECKING:
    from tests.harness.deployment import BaseTestDeployment
    from tests.harness.harness import TestHarness


class ServerType(str, Enum):
    """Enum for the different types of server deployment methods."""

    NONE = "none"
    LOCAL = "local"
    DOCKER = "docker"
    EXTERNAL = "external"


class DatabaseType(str, Enum):
    """Enum for the different types of database deployment methods."""

    SQLITE = "sqlite"
    MYSQL = "mysql"
    MARIADB = "mariadb"
    EXTERNAL = "external"


class DeploymentStoreConfig(BaseTestSecretConfigModel):
    """Configuration for the ZenML store required to connect to the deployment."""

    url: str
    model_config = ConfigDict(validate_assignment=True, extra="allow")


class DeploymentConfig(BaseTestConfigModel):
    """ZenML deployment settings."""

    name: str = Field(pattern="^[a-z][a-z0-9-_]+$")
    description: str = ""
    server: ServerType = ServerType.LOCAL
    database: DatabaseType = DatabaseType.SQLITE
    config: Optional[DeploymentStoreConfig] = None
    disabled: bool = False
    capabilities: Dict[str, bool] = Field(default_factory=dict)

    def get_deployment(self) -> "BaseTestDeployment":
        """Instantiate a test deployment based on this configuration.

        Returns:
            A test deployment instance.
        """
        from tests.harness.deployment import BaseTestDeployment

        return BaseTestDeployment.from_config(self)

    def compile(self, harness: "TestHarness") -> None:
        """Validates and compiles the configuration when part of a test harness.

        Checks that all secrets referenced in the store configuration are
        defined in the test harness.

        Args:
            harness: The test harness to validate against.
        """
        if self.config is not None:
            self.config.compile(harness)
