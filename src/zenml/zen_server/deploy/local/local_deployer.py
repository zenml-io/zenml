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
"""Zen Server local deployer implementation."""

import ipaddress
import os
import shutil
from typing import ClassVar, List, Optional, Union, cast
from zenml.config.global_config import GlobalConfiguration
from zenml.enums import StoreType

from zenml.logger import get_logger
from zenml.utils.io_utils import get_global_config_directory
from zenml.zen_server.deploy.base_deployer import (
    BaseServerDeployer,
    BaseServerDeployment,
    BaseServerDeploymentConfig,
    BaseServerDeploymentStatus,
)
from zenml.zen_server.deploy.local.local_zen_server import (
    LocalZenServer,
    LocalZenServerConfig,
)
from zenml.zen_stores.base_zen_store import DEFAULT_USERNAME
from zenml.zen_stores.rest_zen_store import RestZenStoreConfiguration

logger = get_logger(__name__)

LOCAL_PROVIDER_NAME = "local"

LOCAL_SERVER_SINGLETON_NAME = "local"

LOCAL_DEFAULT_TIMEOUT = 30

LOCAL_ZENML_SERVER_CONFIG_PATH = os.path.join(
    get_global_config_directory(),
    "zen_server",
    "local",
)
LOCAL_ZENML_SERVER_CONFIG_FILENAME = os.path.join(
    LOCAL_ZENML_SERVER_CONFIG_PATH, "service.json"
)


class LocalServerDeploymentStatus(BaseServerDeploymentStatus):
    """Local server deployment status.

    Attributes:
    """

    url: str


class LocalServerDeploymentConfig(BaseServerDeploymentConfig):
    """Local server deployment configuration.

    Attributes:
        port: The TCP port number where the server is accepting connections.
        address: The IP address where the server is reachable.
    """

    port: int = 8237
    address: Union[
        ipaddress.IPv4Address, ipaddress.IPv6Address
    ] = ipaddress.IPv4Address("127.0.0.1")


class LocalServerDeployment(BaseServerDeployment):
    """Local server deployment.

    Attributes:
        config: The local server deployment configuration.
        status: The local server deployment status.
    """

    config: LocalServerDeploymentConfig
    status: LocalServerDeploymentStatus


class LocalServerDeployer(BaseServerDeployer):
    """Local ZenML server deployer."""

    PROVIDER: ClassVar[str] = LOCAL_PROVIDER_NAME

    def _get_local_service(self) -> Optional[LocalZenServer]:
        """Get the local ZenML server service.

        Returns:
            The local ZenML server service or None, if the local server
            deployment is not found.
        """
        from zenml.services import ServiceRegistry

        try:
            with open(LOCAL_ZENML_SERVER_CONFIG_FILENAME, "r") as f:
                return ServiceRegistry().load_service_from_json(f.read())
        except FileNotFoundError:
            return None

    def _copy_global_configuration(self) -> str:
        """Copy the global configuration to the local ZenML server location.

        The local ZenML server global configuration is a copy of the local
        global configuration with the store configuration set to point to the
        local store.

        Returns:
            The path to the ZenML server global configuration.
        """
        gc = GlobalConfiguration()
        server_config_path = os.path.join(
            LOCAL_ZENML_SERVER_CONFIG_PATH, ".zenconfig"
        )

        # this creates a copy of the global configuration with the store
        # set to the local store and saves it to the server configuration path
        gc.copy_configuration(
            config_path=server_config_path, store_config=gc.get_default_store()
        )

    def up(
        self,
        config: BaseServerDeploymentConfig,
        connect: bool = True,
        timeout: Optional[int] = None,
    ) -> None:
        """Deploy the local ZenML server instance.

        This starts a daemon process that runs the uvicorn server directly on
        the local host configured to use the local SQL store.

        Args:
            config: The server deployment configuration.
            connect: Set to connect to the server after deployment.
            timeout: The timeout in seconds to wait until the deployment is
                successful. If not supplied, a default timeout value of 30
                seconds is used.
        """
        if not isinstance(config, LocalServerDeploymentConfig):
            raise TypeError(
                "Invalid server deployment configuration type. It should be a "
                "LocalServerDeploymentConfig."
            )
        local_config = cast(LocalServerDeploymentConfig, config)

        service_config = LocalZenServerConfig(
            root_runtime_path=LOCAL_ZENML_SERVER_CONFIG_PATH,
            singleton=True,
            ip_address=str(local_config.address),
            port=local_config.port,
        )

        service = self._get_local_service()
        if service is not None:
            if (
                service_config.ip_address == service.config.ip_address
                and service_config.port == service.config.port
            ):
                logger.info(
                    "The local ZenML server is already running with the same "
                    "configuration."
                )
            else:
                logger.info(
                    "The local ZenML server is already running with a "
                    "different configuration."
                )
                logger.info("Updating the local ZenML server.")
                service.stop(timeout=timeout or LOCAL_DEFAULT_TIMEOUT)
                service.update(service_config)
        else:
            logger.info("Starting the local ZenML server.")
            self._copy_global_configuration()
            service = LocalZenServer(service_config)

        if not service.is_running:
            service.start(timeout=timeout or LOCAL_DEFAULT_TIMEOUT)

        if connect:
            self.connect(
                LOCAL_SERVER_SINGLETON_NAME,
                username=local_config.username,
                password=local_config.password,
            )

    def down(self, server: str, timeout: Optional[int] = None) -> None:
        """Tear down the local ZenML server instance.

        Args:
            server: The server deployment name or identifier.

        Raises:
            KeyError: If the local server deployment is not found.
        """

        service = self._get_local_service()
        if service is None:
            raise KeyError("The local ZenML server is not deployed.")

        self.disconnect(server)

        logger.info("Shutting down the local ZenML server.")
        service.stop(timeout=timeout or LOCAL_DEFAULT_TIMEOUT)
        shutil.rmtree(LOCAL_ZENML_SERVER_CONFIG_PATH)

    def status(self, server: str) -> BaseServerDeploymentStatus:
        """Get the status of the local ZenML server instance.

        Args:
            server: The server deployment name or identifier.

        Returns:
            The server deployment status.
        """
        local_server = self.get(LOCAL_SERVER_SINGLETON_NAME)
        return local_server.status

    def connect(self, server: str, username: str, password: str) -> None:
        """Connect to the local ZenML server instance.

        Args:
            server: The server deployment name, identifier or URL.
            username: The username to use to connect to the server.
            password: The password to use to connect to the server.
        """

        gc = GlobalConfiguration()

        if server != LOCAL_SERVER_SINGLETON_NAME:
            raise KeyError(
                f"The {server} local ZenML server could not be found."
            )

        service = self._get_local_service()
        if service is None:
            raise KeyError("The local ZenML server could not be found.")

        url = service.endpoint.status.uri
        if not url:
            raise RuntimeError("The local ZenML server is not accessible.")

        store_config = RestZenStoreConfiguration(
            url=url, username=DEFAULT_USERNAME, password=""
        )

        if gc.store == store_config:
            logger.info("ZenML is already connected to the local ZenML server.")
            return

        gc.set_store(store_config)

    def disconnect(self, server: str) -> None:
        """Disconnect from the local ZenML server instance.

        Args:
            server: The server deployment name, identifier or URL.
        """

        gc = GlobalConfiguration()

        if not gc.store or gc.store.type != StoreType.REST:
            logger.info("ZenML is not currently connected to a ZenML server.")
            return

        if server != LOCAL_SERVER_SINGLETON_NAME:
            raise KeyError(
                f"The {server} local ZenML server could not be found."
            )

        service = self._get_local_service()
        if service is None:
            raise KeyError("The local ZenML server could not be found.")

        url = service.endpoint.status.uri
        # TODO: we must be able to disconnect from a server even when it's
        # not accessible.
        if not url:
            raise RuntimeError("The local ZenML server is not accessible.")

        if gc.store.url != url:
            logger.info(
                "ZenML is not currently connected to the local ZenML server."
            )
            return

        gc.set_default_store()

    def get(self, server: str) -> BaseServerDeployment:
        """Get the local server deployment.

        Args:
            server: The server deployment name, identifier or URL.

        Returns:
            The requested server deployment or None, if no server deployment
            could be found corresponding to the given name, identifier or URL.

        Raises:
            KeyError: If the server deployment is not found.
        """

        from zenml.services import ServiceState

        if server != LOCAL_SERVER_SINGLETON_NAME:
            raise KeyError(
                f"The {server} local ZenML server could not be found."
            )

        service = self._get_local_service()
        if service is None:
            raise KeyError("The local ZenML server could not be found.")

        service_status = service.check_status()
        gc = GlobalConfiguration()
        uri = service.endpoint.status.uri or ""
        connected = uri and gc.store and gc.store.url == uri

        return LocalServerDeployment(
            config=LocalServerDeploymentConfig(
                name=LOCAL_SERVER_SINGLETON_NAME,
                address=service.config.ip_address,
                port=service.config.port,
                # TODO: the deployment configuration cannot be fully
                # reconstructed from the service config (some fields are client
                # related).
                username="",
                password="",
            ),
            status=LocalServerDeploymentStatus(
                url=uri,
                deployed=True,
                running=service_status[0] == ServiceState.ACTIVE,
                connected=connected,
            ),
        )

    def list(self) -> List[BaseServerDeployment]:
        """List all server deployments.

        Returns:
            The list of server deployments.
        """
        try:
            local_server = self.get(LOCAL_SERVER_SINGLETON_NAME)
            return [local_server]
        except KeyError:
            return []
