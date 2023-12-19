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
"""External ZenML server deployment."""

from typing import Optional

from tests.harness.deployment.base import BaseTestDeployment
from tests.harness.model import (
    DatabaseType,
    DeploymentConfig,
    DeploymentStoreConfig,
    ServerType,
)


class ExternalServerTestDeployment(BaseTestDeployment):
    """An external server deployment."""

    def __init__(self, config: DeploymentConfig) -> None:
        """Initializes the deployment.

        Args:
            config: The deployment config.

        Raises:
            ValueError: If the config is invalid.
        """
        super().__init__(config)

        if config.config is None:
            raise ValueError(
                "External server deployments must include a configuration."
            )

    @property
    def is_running(self) -> bool:
        """Returns whether the deployment is running.

        Returns:
            Whether the deployment is running.
        """
        try:
            with self.connect() as client:
                _ = client.zen_store
                return True
        except RuntimeError:
            return False

    def up(self) -> None:
        """Starts up the deployment."""

    def down(self) -> None:
        """Tears down the deployment."""

    def get_store_config(self) -> Optional[DeploymentStoreConfig]:
        """Returns the store config for the deployment.

        Returns:
            The store config for the deployment if it is running, None
            otherwise.
        """
        return self.config.config


ExternalServerTestDeployment.register_deployment_class(
    server_type=ServerType.EXTERNAL, database_type=DatabaseType.EXTERNAL
)
