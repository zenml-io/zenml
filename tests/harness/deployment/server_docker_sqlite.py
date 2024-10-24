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
"""Docker ZenML server deployment."""

import logging
from typing import TYPE_CHECKING, Optional

from tests.harness.deployment.base import (
    LOCAL_ZENML_SERVER_DEFAULT_PORT,
    ZENML_SERVER_IMAGE_NAME,
    BaseTestDeployment,
)
from tests.harness.deployment.client_sqlite import ClientSQLiteTestDeployment
from tests.harness.model import (
    DatabaseType,
    DeploymentConfig,
    DeploymentStoreConfig,
    ServerType,
)

if TYPE_CHECKING:
    from zenml.zen_server.deploy.deployment import LocalServerDeployment


class ServerDockerTestDeployment(BaseTestDeployment):
    """A deployment that runs a ZenML server as a docker container."""

    def __init__(self, config: DeploymentConfig) -> None:
        """Initializes a docker ZenML server deployment.

        Args:
            config: The configuration for the deployment.
        """
        super().__init__(config)

        # The server docker deployment is built on top of a local default
        # deployment because the server is provisioned through the client
        self.default_deployment = ClientSQLiteTestDeployment(config)

    @property
    def server(self) -> Optional["LocalServerDeployment"]:
        """Returns the ZenML server corresponding to this configuration.

        Returns:
            The server for the deployment if it exists, None otherwise.
        """
        from zenml.enums import ServerProviderType
        from zenml.zen_server.deploy.deployer import LocalServerDeployer
        from zenml.zen_server.deploy.exceptions import (
            ServerDeploymentNotFoundError,
        )

        # Managing the local server deployment is done through a default
        # local deployment with the same config.
        with self.default_deployment.connect():
            deployer = LocalServerDeployer()
            try:
                server = deployer.get_server()
            except ServerDeploymentNotFoundError:
                return None
            if (
                server is not None
                and server.config.provider == ServerProviderType.DOCKER
            ):
                return server

            return None

    @property
    def is_running(self) -> bool:
        """Returns whether the deployment is running.

        Returns:
            Whether the deployment is running.
        """
        server = self.server
        if server is not None and server.is_running:
            return True

        return False

    def up(self) -> None:
        """Starts up the deployment.

        Raises:
            RuntimeError: If the deployment could not be started.
        """
        from zenml.enums import ServerProviderType
        from zenml.utils.networking_utils import scan_for_available_port
        from zenml.zen_server.deploy.deployer import LocalServerDeployer
        from zenml.zen_server.deploy.deployment import (
            LocalServerDeploymentConfig,
        )

        if self.is_running:
            logging.info(
                f"Deployment '{self.config.name}' is already running. "
                f"Skipping provisioning."
            )
            return

        self.default_deployment.up()

        self.build_server_image()

        # Managing the local server deployment is done through the default
        # deployment with the same config.
        with self.default_deployment.connect():
            port = scan_for_available_port(LOCAL_ZENML_SERVER_DEFAULT_PORT)

            if port is None:
                raise RuntimeError(
                    "Could not find an available port for the ZenML server."
                )

            deployer = LocalServerDeployer()
            server_config = LocalServerDeploymentConfig(
                provider=ServerProviderType.DOCKER,
                port=port,
                image=ZENML_SERVER_IMAGE_NAME,
            )
            deployer.deploy_server(server_config)

        logging.info(
            f"Started ZenML server for deployment '{self.config.name}'."
        )

    def down(self) -> None:
        """Tears down the deployment."""
        from zenml.zen_server.deploy.deployer import LocalServerDeployer

        server = self.server
        if server is not None:
            # Managing the local server deployment is done through the default
            # deployment with the same config.
            with self.default_deployment.connect():
                deployer = LocalServerDeployer()
                deployer.remove_server()

        self.default_deployment.down()

    def get_store_config(self) -> Optional[DeploymentStoreConfig]:
        """Returns the store config for the deployment.

        Returns:
            The store config for the deployment if it is running, None
            otherwise.

        Raises:
            RuntimeError: If the deployment is not running.
        """
        if not self.is_running:
            raise RuntimeError(
                f"The {self.config.name} deployment is not running."
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
        )


ServerDockerTestDeployment.register_deployment_class(
    server_type=ServerType.DOCKER, database_type=DatabaseType.SQLITE
)
