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
"""Base ZenML server provider class."""

from abc import ABC, abstractmethod
from typing import ClassVar, Generator, List, Optional, Tuple, Type

from pydantic import ValidationError

from zenml.config.global_config import GlobalConfiguration
from zenml.enums import ServerProviderType
from zenml.logger import get_logger
from zenml.services import (
    BaseService,
    ServiceConfig,
    ServiceEndpointConfig,
    ServiceEndpointHealthMonitorConfig,
)
from zenml.zen_server.deploy.deployment import (
    ServerDeployment,
    ServerDeploymentConfig,
    ServerDeploymentStatus,
)
from zenml.zen_server.deploy.exceptions import (
    ServerDeploymentConfigurationError,
    ServerDeploymentExistsError,
    ServerDeploymentNotFoundError,
)

logger = get_logger(__name__)


class BaseServerProvider(ABC):
    """Base ZenML server provider class.

    All ZenML server providers must extend and implement this base class.
    """

    TYPE: ClassVar[ServerProviderType]
    CONFIG_TYPE: ClassVar[Type[ServerDeploymentConfig]] = (
        ServerDeploymentConfig
    )

    @classmethod
    def register_as_provider(cls) -> None:
        """Register the class as a server provider."""
        from zenml.zen_server.deploy.deployer import ServerDeployer

        ServerDeployer.register_provider(cls)

    @classmethod
    def _convert_config(
        cls, config: ServerDeploymentConfig
    ) -> ServerDeploymentConfig:
        """Convert a generic server deployment config into a provider specific config.

        Args:
            config: The generic server deployment config.

        Returns:
            The provider specific server deployment config.

        Raises:
            ServerDeploymentConfigurationError: If the configuration is not
                valid.
        """
        if isinstance(config, cls.CONFIG_TYPE):
            return config
        try:
            return cls.CONFIG_TYPE(**config.model_dump())
        except ValidationError as e:
            raise ServerDeploymentConfigurationError(
                f"Invalid configuration for provider {cls.TYPE.value}: {e}"
            )

    def deploy_server(
        self,
        config: ServerDeploymentConfig,
        timeout: Optional[int] = None,
    ) -> ServerDeployment:
        """Deploy a new ZenML server.

        Args:
            config: The generic server deployment configuration.
            timeout: The timeout in seconds to wait until the deployment is
                successful. If not supplied, the default timeout value specified
                by the provider is used.

        Returns:
            The newly created server deployment.

        Raises:
            ServerDeploymentExistsError: If a deployment with the same name
                already exists.
        """
        try:
            self._get_service(config.name)
        except KeyError:
            pass
        else:
            raise ServerDeploymentExistsError(
                f"ZenML server deployment with name '{config.name}' already "
                f"exists"
            )

        # convert the generic deployment config to a provider specific
        # deployment config
        config = self._convert_config(config)
        service = self._create_service(config, timeout)
        return self._get_deployment(service)

    def update_server(
        self,
        config: ServerDeploymentConfig,
        timeout: Optional[int] = None,
    ) -> ServerDeployment:
        """Update an existing ZenML server deployment.

        Args:
            config: The new generic server deployment configuration.
            timeout: The timeout in seconds to wait until the update is
                successful. If not supplied, the default timeout value specified
                by the provider is used.

        Returns:
            The updated server deployment.

        Raises:
            ServerDeploymentNotFoundError: If a deployment with the given name
                doesn't exist.
        """
        try:
            service = self._get_service(config.name)
        except KeyError:
            raise ServerDeploymentNotFoundError(
                f"ZenML server deployment with name '{config.name}' was not "
                f"found"
            )

        # convert the generic deployment config to a provider specific
        # deployment config
        config = self._convert_config(config)
        old_config = self._get_deployment_config(service)

        if old_config == config:
            logger.info(
                f"The {config.name} ZenML server is already configured with "
                f"the same parameters."
            )
            service = self._start_service(service, timeout)
        else:
            logger.info(f"Updating the {config.name} ZenML server.")
            service = self._update_service(service, config, timeout)

        return self._get_deployment(service)

    def remove_server(
        self,
        config: ServerDeploymentConfig,
        timeout: Optional[int] = None,
    ) -> None:
        """Tears down and removes all resources and files associated with a ZenML server deployment.

        Args:
            config: The generic server deployment configuration.
            timeout: The timeout in seconds to wait until the server is
                removed. If not supplied, the default timeout value specified
                by the provider is used.

        Raises:
            ServerDeploymentNotFoundError: If a deployment with the given name
                doesn't exist.
        """
        try:
            service = self._get_service(config.name)
        except KeyError:
            raise ServerDeploymentNotFoundError(
                f"ZenML server deployment with name '{config.name}' was not "
                f"found"
            )

        logger.info(f"Removing the {config.name} ZenML server.")
        self._delete_service(service, timeout)

    def get_server(
        self,
        config: ServerDeploymentConfig,
    ) -> ServerDeployment:
        """Retrieve information about a ZenML server deployment.

        Args:
            config: The generic server deployment configuration.

        Returns:
            The server deployment.

        Raises:
            ServerDeploymentNotFoundError: If a deployment with the given name
                doesn't exist.
        """
        try:
            service = self._get_service(config.name)
        except KeyError:
            raise ServerDeploymentNotFoundError(
                f"ZenML server deployment with name '{config.name}' was not "
                f"found"
            )

        return self._get_deployment(service)

    def list_servers(self) -> List[ServerDeployment]:
        """List all server deployments managed by this provider.

        Returns:
            The list of server deployments.
        """
        return [
            self._get_deployment(service) for service in self._list_services()
        ]

    def get_server_logs(
        self,
        config: ServerDeploymentConfig,
        follow: bool = False,
        tail: Optional[int] = None,
    ) -> Generator[str, bool, None]:
        """Retrieve the logs of a ZenML server.

        Args:
            config: The generic server deployment configuration.
            follow: if True, the logs will be streamed as they are written
            tail: only retrieve the last NUM lines of log output.

        Returns:
            A generator that can be accessed to get the service logs.

        Raises:
            ServerDeploymentNotFoundError: If a deployment with the given name
                doesn't exist.
        """
        try:
            service = self._get_service(config.name)
        except KeyError:
            raise ServerDeploymentNotFoundError(
                f"ZenML server deployment with name '{config.name}' was not "
                f"found"
            )

        return service.get_logs(follow=follow, tail=tail)

    def _get_deployment_status(
        self, service: BaseService
    ) -> ServerDeploymentStatus:
        """Get the status of a server deployment from its service.

        Args:
            service: The server deployment service.

        Returns:
            The status of the server deployment.
        """
        gc = GlobalConfiguration()
        url: Optional[str] = None
        if service.is_running:
            # all services must have an endpoint
            assert service.endpoint is not None

            url = service.endpoint.status.uri
        connected = url is not None and gc.store_configuration.url == url

        return ServerDeploymentStatus(
            url=url,
            status=service.status.state,
            status_message=service.status.last_error,
            connected=connected,
        )

    def _get_deployment(self, service: BaseService) -> ServerDeployment:
        """Get the server deployment associated with a service.

        Args:
            service: The service.

        Returns:
            The server deployment.
        """
        config = self._get_deployment_config(service)

        return ServerDeployment(
            config=config,
            status=self._get_deployment_status(service),
        )

    @classmethod
    @abstractmethod
    def _get_service_configuration(
        cls,
        server_config: ServerDeploymentConfig,
    ) -> Tuple[
        ServiceConfig,
        ServiceEndpointConfig,
        ServiceEndpointHealthMonitorConfig,
    ]:
        """Construct the service configuration from a server deployment configuration.

        Args:
            server_config: server deployment configuration.

        Returns:
            The service, service endpoint and endpoint monitor configuration.
        """

    @abstractmethod
    def _create_service(
        self,
        config: ServerDeploymentConfig,
        timeout: Optional[int] = None,
    ) -> BaseService:
        """Create, start and return a service instance for a ZenML server deployment.

        Args:
            config: The server deployment configuration.
            timeout: The timeout in seconds to wait until the service is
                running. If not supplied, a default timeout value specified
                by the provider implementation should be used.

        Returns:
            The service instance.
        """

    @abstractmethod
    def _update_service(
        self,
        service: BaseService,
        config: ServerDeploymentConfig,
        timeout: Optional[int] = None,
    ) -> BaseService:
        """Update an existing service instance for a ZenML server deployment.

        Args:
            service: The service instance.
            config: The new server deployment configuration.
            timeout: The timeout in seconds to wait until the updated service is
                running. If not supplied, a default timeout value specified
                by the provider implementation should be used.

        Returns:
            The updated service instance.
        """

    @abstractmethod
    def _start_service(
        self,
        service: BaseService,
        timeout: Optional[int] = None,
    ) -> BaseService:
        """Start a service instance for a ZenML server deployment.

        Args:
            service: The service instance.
            timeout: The timeout in seconds to wait until the service is
                running. If not supplied, a default timeout value specified
                by the provider implementation should be used.

        Returns:
            The updated service instance.
        """

    @abstractmethod
    def _stop_service(
        self,
        service: BaseService,
        timeout: Optional[int] = None,
    ) -> BaseService:
        """Stop a service instance for a ZenML server deployment.

        Args:
            service: The service instance.
            timeout: The timeout in seconds to wait until the service is
                stopped. If not supplied, a default timeout value specified
                by the provider implementation should be used.

        Returns:
            The updated service instance.
        """

    @abstractmethod
    def _delete_service(
        self,
        service: BaseService,
        timeout: Optional[int] = None,
    ) -> None:
        """Remove a service instance for a ZenML server deployment.

        Args:
            service: The service instance.
            timeout: The timeout in seconds to wait until the service is
                removed. If not supplied, a default timeout value specified
                by the provider implementation should be used.
        """

    @abstractmethod
    def _get_service(self, server_name: str) -> BaseService:
        """Get the service instance associated with a ZenML server deployment.

        Args:
            server_name: The server deployment name.

        Returns:
            The service instance.

        Raises:
            KeyError: If the server deployment is not found.
        """

    @abstractmethod
    def _list_services(self) -> List[BaseService]:
        """Get all service instances for all deployed ZenML servers.

        Returns:
            A list of service instances.
        """

    @abstractmethod
    def _get_deployment_config(
        self, service: BaseService
    ) -> ServerDeploymentConfig:
        """Recreate the server deployment config from a service instance.

        Args:
            service: The service instance.

        Returns:
            The server deployment config.
        """
