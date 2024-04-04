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
"""Local ZenML server deployment service implementation."""

import ipaddress
import os
from typing import Dict, List, Optional, Tuple, Union, cast

from zenml.client import Client
from zenml.config.global_config import GlobalConfiguration
from zenml.config.store_config import StoreConfiguration
from zenml.constants import (
    DEFAULT_LOCAL_SERVICE_IP_ADDRESS,
    ENV_ZENML_CONFIG_PATH,
    ENV_ZENML_DISABLE_DATABASE_MIGRATION,
    ENV_ZENML_LOCAL_STORES_PATH,
    ENV_ZENML_SERVER_DEPLOYMENT_TYPE,
    ZEN_SERVER_ENTRYPOINT,
)
from zenml.enums import StoreType
from zenml.logger import get_logger
from zenml.models import ServerDeploymentType
from zenml.services import (
    LocalDaemonService,
    LocalDaemonServiceConfig,
    LocalDaemonServiceEndpoint,
    ServiceType,
)
from zenml.utils.io_utils import get_global_config_directory
from zenml.zen_server.deploy.deployment import ServerDeploymentConfig

logger = get_logger(__name__)

ZEN_SERVER_HEALTHCHECK_URL_PATH = "health"
LOCAL_ZENML_SERVER_DEFAULT_TIMEOUT = 30


class LocalServerDeploymentConfig(ServerDeploymentConfig):
    """Local server deployment configuration.

    Attributes:
        port: The TCP port number where the server is accepting connections.
        address: The IP address where the server is reachable.
        blocking: Run the server in blocking mode instead of using a daemon
            process.
    """

    port: int = 8237
    ip_address: Union[ipaddress.IPv4Address, ipaddress.IPv6Address] = (
        ipaddress.IPv4Address(DEFAULT_LOCAL_SERVICE_IP_ADDRESS)
    )
    blocking: bool = False
    store: Optional[StoreConfiguration] = None

    class Config:
        """Pydantic configuration."""

        extra = "forbid"


class LocalZenServerConfig(LocalDaemonServiceConfig):
    """Local Zen server configuration.

    Attributes:
        server: The deployment configuration.
    """

    server: LocalServerDeploymentConfig


class LocalZenServer(LocalDaemonService):
    """Service daemon that can be used to start a local ZenML Server.

    Attributes:
        config: service configuration
        endpoint: optional service endpoint
    """

    SERVICE_TYPE = ServiceType(
        name="local_zenml_server",
        type="zen_server",
        flavor="local",
        description="Local ZenML server deployment",
    )

    config: LocalZenServerConfig
    endpoint: LocalDaemonServiceEndpoint

    @classmethod
    def config_path(cls) -> str:
        """Path to the directory where the local ZenML server files are located.

        Returns:
            Path to the local ZenML server runtime directory.
        """
        return os.path.join(
            get_global_config_directory(),
            "zen_server",
            "local",
        )

    @property
    def _global_config_path(self) -> str:
        """Path to the global configuration directory used by this server.

        Returns:
            Path to the global configuration directory used by this server.
        """
        return os.path.join(self.config_path(), ".zenconfig")

    @classmethod
    def get_service(cls) -> Optional["LocalZenServer"]:
        """Load and return the local ZenML server service, if present.

        Returns:
            The local ZenML server service or None, if the local server
            deployment is not found.
        """
        config_filename = os.path.join(cls.config_path(), "service.json")
        try:
            with open(config_filename, "r") as f:
                return cast(
                    "LocalZenServer", LocalZenServer.from_json(f.read())
                )
        except FileNotFoundError:
            return None

    def _get_daemon_cmd(self) -> Tuple[List[str], Dict[str, str]]:
        """Get the command to start the daemon.

        Overrides the base class implementation to add the environment variable
        that forces the ZenML server to use the copied global config.

        Returns:
            The command to start the daemon and the environment variables to
            set for the command.
        """
        cmd, env = super()._get_daemon_cmd()
        env[ENV_ZENML_CONFIG_PATH] = self._global_config_path
        env[ENV_ZENML_SERVER_DEPLOYMENT_TYPE] = ServerDeploymentType.LOCAL
        # Set the local stores path to the same path used by the client. This
        # ensures that the server's default store configuration is initialized
        # to point at the same local SQLite database as the client.
        env[ENV_ZENML_LOCAL_STORES_PATH] = (
            GlobalConfiguration().local_stores_path
        )
        env[ENV_ZENML_DISABLE_DATABASE_MIGRATION] = "True"

        return cmd, env

    def provision(self) -> None:
        """Provision the service."""
        super().provision()

    def start(self, timeout: int = 0) -> None:
        """Start the service and optionally wait for it to become active.

        Args:
            timeout: amount of time to wait for the service to become active.
                If set to 0, the method will return immediately after checking
                the service status.
        """
        if not self.config.blocking:
            super().start(timeout)
        else:
            # In the blocking mode, we need to temporarily set the environment
            # variables for the running process to make it look like the server
            # is running in a separate environment (i.e. using a different
            # global configuration path). This is necessary to avoid polluting
            # the client environment with the server's configuration.
            local_stores_path = GlobalConfiguration().local_stores_path
            GlobalConfiguration._reset_instance()
            Client._reset_instance()
            original_config_path = os.environ.get(ENV_ZENML_CONFIG_PATH)
            os.environ[ENV_ZENML_CONFIG_PATH] = self._global_config_path
            # Set the local stores path to the same path used by the client.
            # This ensures that the server's default store configuration is
            # initialized to point at the same local SQLite database as the
            # client.
            os.environ[ENV_ZENML_LOCAL_STORES_PATH] = local_stores_path
            try:
                self.run()
            finally:
                # Restore the original client environment variables
                if original_config_path:
                    os.environ[ENV_ZENML_CONFIG_PATH] = original_config_path
                else:
                    del os.environ[ENV_ZENML_CONFIG_PATH]
                del os.environ[ENV_ZENML_LOCAL_STORES_PATH]
                GlobalConfiguration._reset_instance()
                Client._reset_instance()

    def run(self) -> None:
        """Run the ZenML Server.

        Raises:
            ValueError: if started with a global configuration that connects to
                another ZenML server.
        """
        import uvicorn

        gc = GlobalConfiguration()
        if gc.store_configuration.type == StoreType.REST:
            raise ValueError(
                "The ZenML server cannot be started with REST store type."
            )
        logger.info(
            "Starting ZenML Server as blocking "
            "process... press CTRL+C once to stop it."
        )

        self.endpoint.prepare_for_start()

        try:
            uvicorn.run(
                ZEN_SERVER_ENTRYPOINT,
                host=self.endpoint.config.ip_address,
                port=self.endpoint.config.port or 8000,
                log_level="info",
                server_header=False,
            )
        except KeyboardInterrupt:
            logger.info("ZenML Server stopped. Resuming normal execution.")
