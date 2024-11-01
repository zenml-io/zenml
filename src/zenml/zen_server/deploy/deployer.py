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
"""ZenML server deployer singleton implementation."""

from typing import ClassVar, Dict, Generator, Optional, Type

from zenml.config.global_config import GlobalConfiguration
from zenml.enums import ServerProviderType, StoreType
from zenml.logger import get_logger
from zenml.utils.singleton import SingletonMetaClass
from zenml.zen_server.deploy.base_provider import BaseServerProvider
from zenml.zen_server.deploy.deployment import (
    LocalServerDeployment,
    LocalServerDeploymentConfig,
)
from zenml.zen_server.deploy.exceptions import (
    ServerDeploymentError,
    ServerDeploymentNotFoundError,
    ServerProviderNotFoundError,
)
from zenml.zen_stores.base_zen_store import BaseZenStore
from zenml.zen_stores.rest_zen_store import RestZenStoreConfiguration

logger = get_logger(__name__)


class LocalServerDeployer(metaclass=SingletonMetaClass):
    """Local server deployer singleton.

    This class is responsible for managing the various server provider
    implementations and for directing server deployment lifecycle requests to
    the responsible provider. It acts as a facade built on top of the various
    server providers.
    """

    _providers: ClassVar[Dict[ServerProviderType, BaseServerProvider]] = {}

    @classmethod
    def register_provider(cls, provider: Type[BaseServerProvider]) -> None:
        """Register a server provider.

        Args:
            provider: The server provider to register.

        Raises:
            TypeError: If a provider with the same type is already registered.
        """
        if provider.TYPE in cls._providers:
            raise TypeError(
                f"Server provider '{provider.TYPE}' is already registered."
            )
        logger.debug(f"Registering server provider '{provider.TYPE}'.")
        cls._providers[provider.TYPE] = provider()

    @classmethod
    def get_provider(
        cls, provider_type: ServerProviderType
    ) -> BaseServerProvider:
        """Get the server provider associated with a provider type.

        Args:
            provider_type: The server provider type.

        Returns:
            The server provider associated with the provider type.

        Raises:
            ServerProviderNotFoundError: If no provider is registered for the
                given provider type.
        """
        if provider_type not in cls._providers:
            raise ServerProviderNotFoundError(
                f"Server provider '{provider_type}' is not registered."
            )
        return cls._providers[provider_type]

    def initialize_local_database(self) -> None:
        """Initialize the local ZenML database."""
        default_store_cfg = GlobalConfiguration().get_default_store()
        BaseZenStore.create_store(default_store_cfg)

    def deploy_server(
        self,
        config: LocalServerDeploymentConfig,
        timeout: Optional[int] = None,
        restart: bool = False,
    ) -> LocalServerDeployment:
        """Deploy the local ZenML server or update the existing deployment.

        Args:
            config: The server deployment configuration.
            timeout: The timeout in seconds to wait until the deployment is
                successful. If not supplied, the default timeout value specified
                by the provider is used.
            restart: If True, the existing server deployment will be torn down
                and a new server will be deployed.

        Returns:
            The local server deployment.
        """
        # Ensure that the local database is always initialized before any local
        # server is deployed or updated.
        self.initialize_local_database()

        try:
            self.get_server()
        except ServerDeploymentNotFoundError:
            pass
        else:
            return self.update_server(
                config=config, timeout=timeout, restart=restart
            )

        provider_name = config.provider.value
        provider = self.get_provider(config.provider)

        logger.info(f"Deploying a local {provider_name} ZenML server.")
        return provider.deploy_server(config, timeout=timeout)

    def update_server(
        self,
        config: LocalServerDeploymentConfig,
        timeout: Optional[int] = None,
        restart: bool = False,
    ) -> LocalServerDeployment:
        """Update an existing local ZenML server deployment.

        Args:
            config: The new server deployment configuration.
            timeout: The timeout in seconds to wait until the deployment is
                successful. If not supplied, a default timeout value of 30
                seconds is used.
            restart: If True, the existing server deployment will be torn down
                and a new server will be deployed.

        Returns:
            The updated server deployment.
        """
        # this will also raise ServerDeploymentNotFoundError if the server
        # does not exist
        existing_server = self.get_server()

        provider = self.get_provider(config.provider)
        if existing_server.config.provider != config.provider or restart:
            existing_provider = self.get_provider(
                existing_server.config.provider
            )

            # Tear down the existing server deployment
            existing_provider.remove_server(
                existing_server.config, timeout=timeout
            )

            # Deploy a new server with the new provider
            return provider.deploy_server(config, timeout=timeout)

        return provider.update_server(config, timeout=timeout)

    def remove_server(
        self,
        timeout: Optional[int] = None,
    ) -> None:
        """Tears down and removes all resources and files associated with the local ZenML server deployment.

        Args:
            timeout: The timeout in seconds to wait until the deployment is
                successfully torn down. If not supplied, a provider specific
                default timeout value is used.
        """
        # this will also raise ServerDeploymentNotFoundError if the server
        # does not exist
        try:
            server = self.get_server()
        except ServerDeploymentNotFoundError:
            return

        provider_name = server.config.provider.value
        provider = self.get_provider(server.config.provider)

        if self.is_connected_to_server():
            try:
                self.disconnect_from_server()
            except Exception as e:
                logger.warning(
                    f"Failed to disconnect from the local server: {e}"
                )

        logger.info(f"Tearing down the local {provider_name} ZenML server.")
        provider.remove_server(server.config, timeout=timeout)

    def is_connected_to_server(self) -> bool:
        """Check if the ZenML client is currently connected to the local ZenML server.

        Returns:
            True if the ZenML client is connected to the local ZenML server, False
            otherwise.
        """
        # this will also raise ServerDeploymentNotFoundError if the server
        # does not exist
        try:
            server = self.get_server()
        except ServerDeploymentNotFoundError:
            return False

        gc = GlobalConfiguration()
        return (
            server.status is not None
            and server.status.url is not None
            and gc.store_configuration.url == server.status.url
        )

    def connect_to_server(
        self,
    ) -> None:
        """Connect to the local ZenML server instance.

        Raises:
            ServerDeploymentError: If the local ZenML server is not running or
                is unreachable.
        """
        # this will also raise ServerDeploymentNotFoundError if the server
        # does not exist
        server = self.get_server()
        provider_name = server.config.provider.value

        gc = GlobalConfiguration()
        if not server.status or not server.status.url:
            raise ServerDeploymentError(
                f"The local {provider_name} ZenML server is not currently "
                "running or is unreachable."
            )

        store_config = RestZenStoreConfiguration(
            url=server.status.url,
        )

        if gc.store_configuration == store_config:
            logger.info(
                "Your client is already connected to the local "
                f"{provider_name} ZenML server."
            )
            return

        logger.info(
            f"Connecting to the local {provider_name} ZenML server "
            f"({store_config.url})."
        )

        gc.set_store(store_config)

        logger.info(
            f"Connected to the local {provider_name} ZenML server "
            f"({store_config.url})."
        )

    def disconnect_from_server(
        self,
    ) -> None:
        """Disconnect from the ZenML server instance."""
        gc = GlobalConfiguration()
        store_cfg = gc.store_configuration

        if store_cfg.type != StoreType.REST:
            logger.info(
                "Your client is not currently connected to a ZenML server."
            )
            return

        logger.info(
            f"Disconnecting from the local ({store_cfg.url}) ZenML server."
        )

        gc.set_default_store()

        logger.info("Disconnected from the local ZenML server.")

    def get_server(
        self,
    ) -> LocalServerDeployment:
        """Get the local server deployment.

        Returns:
            The local server deployment.

        Raises:
            ServerDeploymentNotFoundError: If no local server deployment is
                found.
        """
        for provider in self._providers.values():
            try:
                return provider.get_server(
                    LocalServerDeploymentConfig(provider=provider.TYPE)
                )
            except ServerDeploymentNotFoundError:
                pass

        raise ServerDeploymentNotFoundError(
            "No local server deployment was found."
        )

    def get_server_logs(
        self,
        follow: bool = False,
        tail: Optional[int] = None,
    ) -> Generator[str, bool, None]:
        """Retrieve the logs for the local ZenML server.

        Args:
            follow: if True, the logs will be streamed as they are written
            tail: only retrieve the last NUM lines of log output.

        Returns:
            A generator that can be accessed to get the service logs.
        """
        # this will also raise ServerDeploymentNotFoundError if the server
        # does not exist
        server = self.get_server()

        provider_name = server.config.provider.value
        provider = self.get_provider(server.config.provider)

        logger.info(
            f"Fetching logs from the local {provider_name} ZenML " f"server..."
        )
        return provider.get_server_logs(
            server.config, follow=follow, tail=tail
        )
