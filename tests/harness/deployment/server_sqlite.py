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
"""Local ZenML server deployment."""

import logging
import sys
from typing import TYPE_CHECKING, Optional

from tests.harness.deployment.base import (
    LOCAL_ZENML_SERVER_DEFAULT_PORT,
    BaseTestDeployment,
)
from tests.harness.deployment.local_sqlite import LocalSqliteTestDeployment
from tests.harness.model import (
    DeploymentConfig,
    DatabaseType,
    DeploymentStoreConfig,
    ServerType,
)

if TYPE_CHECKING:
    from zenml.zen_server.deploy.deployment import ServerDeployment


class ServerSqliteTestDeployment(BaseTestDeployment):
    """A deployment that runs a ZenML server as a background process."""

    def __init__(self, config: DeploymentConfig) -> None:
        """Initializes a local ZenML server deployment.

        Args:
            config: The configuration for the deployment.
        """
        super().__init__(config)

        # The server local deployment is built on top of a local default
        # deployment because the server is provisioned through the client
        self.default_deployment = LocalSqliteTestDeployment(config)

    @property
    def server(self) -> Optional["ServerDeployment"]:
        """Returns the ZenML server corresponding to this configuration.

        Returns:
            The server for the deployment if it exists, None otherwise.
        """
        from zenml.enums import ServerProviderType
        from zenml.zen_server.deploy.deployer import ServerDeployer

        # Managing the local server deployment is done through a default
        # local deployment with the same config.
        with self.default_deployment.connect():
            deployer = ServerDeployer()
            servers = deployer.list_servers(
                provider_type=ServerProviderType.LOCAL
            )
            if not servers:
                return None

            return servers[0]

    @property
    def is_running(self) -> bool:
        """Returns whether the ZenML server is running.

        Returns:
            True if the server is running, False otherwise.
        """
        server = self.server
        if server is not None and server.is_running:
            return True

        return False

    def up(self) -> None:
        """Starts the ZenML deployment.

        Raises:
            RuntimeError: If the deployment is not supported on the host OS.
        """
        from zenml.enums import ServerProviderType
        from zenml.utils.networking_utils import scan_for_available_port
        from zenml.zen_server.deploy.deployer import ServerDeployer
        from zenml.zen_server.deploy.deployment import ServerDeploymentConfig

        if sys.platform == "win32":
            raise RuntimeError(
                "Running the ZenML server locally as a background process is "
                "not supported on Windows."
            )
        else:
            pass

        if self.is_running:
            logging.info(
                f"Deployment '{self.config.name}' is already running. "
                f"Skipping provisioning."
            )
            return

        self.default_deployment.up()

        # Managing the local server deployment is done through the default
        # deployment with the same config.
        with self.default_deployment.connect():
            port = scan_for_available_port(LOCAL_ZENML_SERVER_DEFAULT_PORT)

            if port is None:
                raise RuntimeError(
                    "Could not find an available port for the ZenML server."
                )

            deployer = ServerDeployer()
            server_config = ServerDeploymentConfig(
                name=self.config.name,
                provider=ServerProviderType.LOCAL,
                port=port,
            )
            deployer.deploy_server(server_config)

        logging.info(
            f"Started ZenML server for deployment '{self.config.name}'."
        )

    def down(self) -> None:
        """Stops the ZenML deployment."""
        from zenml.zen_server.deploy.deployer import ServerDeployer

        server = self.server
        if server is None:
            logging.info(
                f"Deployment '{self.config.name}' is no longer running. "
            )
            return

        # Managing the local server deployment is done through the default
        # deployment with the same config.
        with self.default_deployment.connect():
            deployer = ServerDeployer()
            deployer.remove_server(server.config.name)

        self.default_deployment.down()

    def get_store_config(self) -> Optional[DeploymentStoreConfig]:
        """Returns the store config for the deployment.

        Returns:
            The store config for the deployment if it is running, None
            otherwise.

        Raises:
            RuntimeError: If the deployment is not running.
        """
        from zenml.constants import (
            DEFAULT_PASSWORD,
            DEFAULT_USERNAME,
        )

        if not self.is_running:
            raise RuntimeError(
                f"The '{self.config.name}' deployment is not running."
            )

        server = self.server
        if (
            server is None
            or server.status is None
            or server.status.url is None
        ):
            raise RuntimeError(
                f"The '{self.config.name}' deployment is not running."
            )

        return DeploymentStoreConfig(
            url=server.status.url,
            username=DEFAULT_USERNAME,
            password=DEFAULT_PASSWORD,
        )


ServerSqliteTestDeployment.register_deployment_class(
    type=ServerType.LOCAL, setup=DatabaseType.SQLITE
)
