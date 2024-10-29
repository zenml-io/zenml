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
from typing import ClassVar, Generator, Optional, Tuple, Type

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
    LocalServerDeployment,
    LocalServerDeploymentConfig,
    LocalServerDeploymentStatus,
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
    CONFIG_TYPE: ClassVar[Type[LocalServerDeploymentConfig]] = (
        LocalServerDeploymentConfig
    )

    @classmethod
    def register_as_provider(cls) -> None:
        """Register the class as a server provider."""
        from zenml.zen_server.deploy.deployer import LocalServerDeployer

        LocalServerDeployer.register_provider(cls)

    @classmethod
    def _convert_config(
        cls, config: LocalServerDeploymentConfig
    ) -> LocalServerDeploymentConfig:
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
        config: LocalServerDeploymentConfig,
        timeout: Optional[int] = None,
    ) -> LocalServerDeployment:
        """Deploy a new ZenML server.

        Args:
            config: The generic server deployment configuration.
            timeout: The timeout in seconds to wait until the deployment is
                successful. If not supplied, the default timeout value specified
                by the provider is used.

        Returns:
            The newly created server deployment.

        Raises:
            ServerDeploymentExistsError: If a deployment already exists.
        """
        try:
            self._get_service()
        except KeyError:
            pass
        else:
            raise ServerDeploymentExistsError(
                f"Local {self.TYPE.value} ZenML server deployment already exists"
            )

        # convert the generic deployment config to a provider specific
        # deployment config
        config = self._convert_config(config)
        service = self._create_service(config, timeout)
        return self._get_deployment(service)

    def update_server(
        self,
        config: LocalServerDeploymentConfig,
        timeout: Optional[int] = None,
    ) -> LocalServerDeployment:
        """Update an existing ZenML server deployment.

        Args:
            config: The new generic server deployment configuration.
            timeout: The timeout in seconds to wait until the update is
                successful. If not supplied, the default timeout value specified
                by the provider is used.

        Returns:
            The updated server deployment.

        Raises:
            ServerDeploymentNotFoundError: If a deployment doesn't exist.
        """
        try:
            service = self._get_service()
        except KeyError:
            raise ServerDeploymentNotFoundError(
                f"The local {self.TYPE.value} ZenML server deployment was not "
                f"found"
            )

        # convert the generic deployment config to a provider specific
        # deployment config
        config = self._convert_config(config)
        old_config = self._get_deployment_config(service)

        if old_config == config:
            logger.info(
                f"The local {self.TYPE.value} ZenML server is already "
                "configured with the same parameters."
            )
            service = self._start_service(service, timeout)
        else:
            logger.info(f"Updating the local {self.TYPE.value} ZenML server.")
            service = self._update_service(service, config, timeout)

        return self._get_deployment(service)

    def remove_server(
        self,
        config: LocalServerDeploymentConfig,
        timeout: Optional[int] = None,
    ) -> None:
        """Tears down and removes all resources and files associated with a ZenML server deployment.

        Args:
            config: The generic server deployment configuration.
            timeout: The timeout in seconds to wait until the server is
                removed. If not supplied, the default timeout value specified
                by the provider is used.

        Raises:
            ServerDeploymentNotFoundError: If a deployment doesn't exist.
        """
        try:
            service = self._get_service()
        except KeyError:
            raise ServerDeploymentNotFoundError(
                f"The local {self.TYPE.value} ZenML server deployment was not "
                f"found"
            )

        logger.info(f"Shutting down the local {self.TYPE.value} ZenML server.")
        self._delete_service(service, timeout)

    def get_server(
        self,
        config: LocalServerDeploymentConfig,
    ) -> LocalServerDeployment:
        """Retrieve information about a ZenML server deployment.

        Args:
            config: The generic server deployment configuration.

        Returns:
            The server deployment.

        Raises:
            ServerDeploymentNotFoundError: If a deployment doesn't exist.
        """
        try:
            service = self._get_service()
        except KeyError:
            raise ServerDeploymentNotFoundError(
                f"The local {self.TYPE.value} ZenML server deployment was not "
                f"found"
            )

        return self._get_deployment(service)

    def get_server_logs(
        self,
        config: LocalServerDeploymentConfig,
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
            ServerDeploymentNotFoundError: If a deployment doesn't exist.
        """
        try:
            service = self._get_service()
        except KeyError:
            raise ServerDeploymentNotFoundError(
                f"The local {self.TYPE.value} ZenML server deployment was not "
                f"found"
            )

        return service.get_logs(follow=follow, tail=tail)

    def _get_deployment_status(
        self, service: BaseService
    ) -> LocalServerDeploymentStatus:
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

        return LocalServerDeploymentStatus(
            url=url,
            status=service.status.state,
            status_message=service.status.last_error,
            connected=connected,
        )

    def _get_deployment(self, service: BaseService) -> LocalServerDeployment:
        """Get the server deployment associated with a service.

        Args:
            service: The service.

        Returns:
            The server deployment.
        """
        config = self._get_deployment_config(service)

        return LocalServerDeployment(
            config=config,
            status=self._get_deployment_status(service),
        )

    @classmethod
    @abstractmethod
    def _get_service_configuration(
        cls,
        server_config: LocalServerDeploymentConfig,
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
        config: LocalServerDeploymentConfig,
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
        config: LocalServerDeploymentConfig,
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
    def _get_service(self) -> BaseService:
        """Get the service instance associated with a ZenML server deployment.

        Returns:
            The service instance.

        Raises:
            KeyError: If the server deployment is not found.
        """

    @abstractmethod
    def _get_deployment_config(
        self, service: BaseService
    ) -> LocalServerDeploymentConfig:
        """Recreate the server deployment config from a service instance.

        Args:
            service: The service instance.

        Returns:
            The server deployment config.
        """
