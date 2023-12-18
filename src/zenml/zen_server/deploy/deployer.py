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

from typing import ClassVar, Dict, Generator, List, Optional, Type, Union

from zenml.config.global_config import GlobalConfiguration
from zenml.enums import ServerProviderType, StoreType
from zenml.logger import get_logger
from zenml.utils.singleton import SingletonMetaClass
from zenml.zen_server.deploy.base_provider import BaseServerProvider
from zenml.zen_server.deploy.deployment import (
    ServerDeployment,
    ServerDeploymentConfig,
)
from zenml.zen_server.deploy.exceptions import (
    ServerDeploymentError,
    ServerDeploymentExistsError,
    ServerDeploymentNotFoundError,
    ServerProviderNotFoundError,
)
from zenml.zen_stores.rest_zen_store import RestZenStoreConfiguration
from zenml.zen_stores.secrets_stores.rest_secrets_store import (
    RestSecretsStoreConfiguration,
)

logger = get_logger(__name__)


class ServerDeployer(metaclass=SingletonMetaClass):
    """Server deployer singleton.

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

    def deploy_server(
        self,
        config: ServerDeploymentConfig,
        timeout: Optional[int] = None,
    ) -> ServerDeployment:
        """Deploy a new ZenML server or update an existing deployment.

        Args:
            config: The server deployment configuration.
            timeout: The timeout in seconds to wait until the deployment is
                successful. If not supplied, the default timeout value specified
                by the provider is used.

        Returns:
            The server deployment.
        """
        # We do this here to ensure that the zenml store is always initialized
        # before the server is deployed. This is necessary because the server
        # may require access to the local store configuration or database.
        gc = GlobalConfiguration()

        _ = gc.zen_store

        try:
            self.get_server(config.name)
        except ServerDeploymentNotFoundError:
            pass
        else:
            return self.update_server(config=config, timeout=timeout)

        provider_name = config.provider.value
        provider = self.get_provider(config.provider)

        logger.info(
            f"Deploying a {provider_name} ZenML server with name "
            f"'{config.name}'."
        )
        return provider.deploy_server(config, timeout=timeout)

    def update_server(
        self,
        config: ServerDeploymentConfig,
        timeout: Optional[int] = None,
    ) -> ServerDeployment:
        """Update an existing ZenML server deployment.

        Args:
            config: The new server deployment configuration.
            timeout: The timeout in seconds to wait until the deployment is
                successful. If not supplied, a default timeout value of 30
                seconds is used.

        Returns:
            The updated server deployment.

        Raises:
            ServerDeploymentExistsError: If an existing deployment with the same
                name but a different provider type is found.
        """
        # this will also raise ServerDeploymentNotFoundError if the server
        # does not exist
        existing_server = self.get_server(config.name)

        provider = self.get_provider(config.provider)
        existing_provider = existing_server.config.provider

        if existing_provider != config.provider:
            raise ServerDeploymentExistsError(
                f"A server deployment with the same name '{config.name}' but "
                f"with a different provider '{existing_provider.value}'."
                f"is already provisioned. Please choose a different name or "
                f"tear down the existing deployment."
            )

        return provider.update_server(config, timeout=timeout)

    def remove_server(
        self,
        server_name: str,
        timeout: Optional[int] = None,
    ) -> None:
        """Tears down and removes all resources and files associated with a ZenML server deployment.

        Args:
            server_name: The server deployment name.
            timeout: The timeout in seconds to wait until the deployment is
                successfully torn down. If not supplied, a provider specific
                default timeout value is used.
        """
        # this will also raise ServerDeploymentNotFoundError if the server
        # does not exist
        server = self.get_server(server_name)

        provider_name = server.config.provider.value
        provider = self.get_provider(server.config.provider)

        if self.is_connected_to_server(server_name):
            try:
                self.disconnect_from_server(server_name)
            except Exception as e:
                logger.warning(f"Failed to disconnect from the server: {e}")

        logger.info(
            f"Tearing down the '{server_name}' {provider_name} ZenML server."
        )
        provider.remove_server(server.config, timeout=timeout)

    def is_connected_to_server(self, server_name: str) -> bool:
        """Check if the ZenML client is currently connected to a ZenML server.

        Args:
            server_name: The server deployment name.

        Returns:
            True if the ZenML client is connected to the ZenML server, False
            otherwise.
        """
        # this will also raise ServerDeploymentNotFoundError if the server
        # does not exist
        server = self.get_server(server_name)

        gc = GlobalConfiguration()
        return (
            server.status is not None
            and server.status.url is not None
            and gc.store is not None
            and gc.store.url == server.status.url
        )

    def connect_to_server(
        self,
        server_name: str,
        username: str,
        password: str,
        verify_ssl: Union[bool, str] = True,
    ) -> None:
        """Connect to a ZenML server instance.

        Args:
            server_name: The server deployment name.
            username: The username to use to connect to the server.
            password: The password to use to connect to the server.
            verify_ssl: Either a boolean, in which case it controls whether we
                verify the server's TLS certificate, or a string, in which case
                it must be a path to a CA bundle to use or the CA bundle value
                itself.

        Raises:
            ServerDeploymentError: If the ZenML server is not running or
                is unreachable.
        """
        # this will also raise ServerDeploymentNotFoundError if the server
        # does not exist
        server = self.get_server(server_name)
        provider_name = server.config.provider.value

        gc = GlobalConfiguration()
        if not server.status or not server.status.url:
            raise ServerDeploymentError(
                f"The {provider_name} {server_name} ZenML "
                f"server is not currently running or is unreachable."
            )

        store_config = RestZenStoreConfiguration(
            url=server.status.url,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
            secrets_store=RestSecretsStoreConfiguration(),
        )

        if gc.store == store_config:
            logger.info(
                f"ZenML is already connected to the '{server_name}' "
                f"{provider_name} ZenML server."
            )
            return

        logger.info(
            f"Connecting ZenML to the '{server_name}' "
            f"{provider_name} ZenML server ({store_config.url})."
        )

        gc.set_store(store_config)

        logger.info(
            f"Connected ZenML to the '{server_name}' "
            f"{provider_name} ZenML server ({store_config.url})."
        )

    def disconnect_from_server(
        self,
        server_name: Optional[str] = None,
    ) -> None:
        """Disconnect from a ZenML server instance.

        Args:
            server_name: The server deployment name. If supplied, the deployer
                will check if the ZenML client is indeed connected to the server
                and disconnect only if that is the case. Otherwise the deployer
                will disconnect from any ZenML server.
        """
        gc = GlobalConfiguration()

        if not gc.store or gc.store.type != StoreType.REST:
            logger.info("ZenML is not currently connected to a ZenML server.")
            return

        if server_name:
            # this will also raise ServerDeploymentNotFoundError if the server
            # does not exist
            server = self.get_server(server_name)
            provider_name = server.config.provider.value

            if not self.is_connected_to_server(server_name):
                logger.info(
                    f"ZenML is not currently connected to the '{server_name}' "
                    f"{provider_name} ZenML server."
                )
                return

            logger.info(
                f"Disconnecting ZenML from the '{server_name}' "
                f"{provider_name} ZenML server ({gc.store.url})."
            )
        else:
            logger.info(
                f"Disconnecting ZenML from the {gc.store.url} ZenML server."
            )

        gc.set_default_store()

        logger.info("Disconnected ZenML from the ZenML server.")

    def get_server(
        self,
        server_name: str,
    ) -> ServerDeployment:
        """Get a server deployment.

        Args:
            server_name: The server deployment name.

        Returns:
            The requested server deployment.

        Raises:
            ServerDeploymentNotFoundError: If no server deployment with the
                given name is found.
        """
        for provider in self._providers.values():
            try:
                return provider.get_server(
                    ServerDeploymentConfig(
                        name=server_name, provider=provider.TYPE
                    )
                )
            except ServerDeploymentNotFoundError:
                pass

        raise ServerDeploymentNotFoundError(
            f"Server deployment '{server_name}' not found."
        )

    def list_servers(
        self,
        server_name: Optional[str] = None,
        provider_type: Optional[ServerProviderType] = None,
    ) -> List[ServerDeployment]:
        """List all server deployments.

        Args:
            server_name: The server deployment name to filter by.
            provider_type: The server provider type to filter by.

        Returns:
            The list of server deployments.
        """
        providers: List[BaseServerProvider] = []
        if provider_type:
            providers = [self.get_provider(provider_type)]
        else:
            providers = list(self._providers.values())

        servers: List[ServerDeployment] = []
        for provider in providers:
            if server_name:
                try:
                    servers.append(
                        provider.get_server(
                            ServerDeploymentConfig(
                                name=server_name,
                                provider=provider.TYPE,
                            )
                        )
                    )
                except ServerDeploymentNotFoundError:
                    pass
            else:
                servers.extend(provider.list_servers())

        return servers

    def get_server_logs(
        self,
        server_name: str,
        follow: bool = False,
        tail: Optional[int] = None,
    ) -> Generator[str, bool, None]:
        """Retrieve the logs of a ZenML server.

        Args:
            server_name: The server deployment name.
            follow: if True, the logs will be streamed as they are written
            tail: only retrieve the last NUM lines of log output.

        Returns:
            A generator that can be accessed to get the service logs.
        """
        # this will also raise ServerDeploymentNotFoundError if the server
        # does not exist
        server = self.get_server(server_name)

        provider_name = server.config.provider.value
        provider = self.get_provider(server.config.provider)

        logger.info(
            f"Fetching logs from the '{server_name}' {provider_name} ZenML "
            f"server..."
        )
        return provider.get_server_logs(
            server.config, follow=follow, tail=tail
        )
