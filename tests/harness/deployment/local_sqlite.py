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
"""Default ZenML deployment."""

import sys
from pathlib import Path
from typing import Optional

from tests.harness.deployment.base import BaseTestDeployment
from tests.harness.model import (
    DatabaseType,
    DeploymentConfig,
    DeploymentStoreConfig,
    ServerType,
)


class LocalSqliteTestDeployment(BaseTestDeployment):
    """Default ZenML deployment."""

    def __init__(self, config: DeploymentConfig) -> None:
        """Initializes the default deployment.

        Args:
            config: The deployment config.
        """
        super().__init__(config)

    @property
    def is_running(self) -> bool:
        """Returns whether the deployment is running.

        Returns:
            Whether the deployment is running.
        """
        return True

    def up(self) -> None:
        """Starts up the deployment."""
        with self.connect() as client:
            # Initialize the default store and database
            _ = client.zen_store

    def down(self) -> None:
        """Tears down the deployment.

        Raises:
            PermissionError: If the database file cannot be deleted.
        """
        from zenml.zen_stores.sql_zen_store import SqlZenStoreConfiguration

        with self.connect() as client:
            # Delete the default store database
            if isinstance(client.zen_store.config, SqlZenStoreConfiguration):
                assert client.zen_store.config.database is not None

                try:
                    Path(client.zen_store.config.database).unlink()
                except PermissionError:
                    if sys.platform == "win32":
                        pass
                    else:
                        raise

    def get_store_config(self) -> Optional[DeploymentStoreConfig]:
        """Returns the store config for the deployment.

        Returns:
            The store config for the deployment if it is running, None
            otherwise.
        """
        return None


LocalSqliteTestDeployment.register_deployment_class(
    type=ServerType.NONE, setup=DatabaseType.SQLITE
)
