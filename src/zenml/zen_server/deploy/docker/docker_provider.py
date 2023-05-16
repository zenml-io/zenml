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
"""Zen Server docker deployer implementation."""

import shutil
from typing import ClassVar, List, Optional, Tuple, Type, cast

from zenml.enums import ServerProviderType
from zenml.logger import get_logger
from zenml.services import (
    BaseService,
    ContainerServiceEndpoint,
    ContainerServiceEndpointConfig,
    HTTPEndpointHealthMonitor,
    HTTPEndpointHealthMonitorConfig,
    ServiceConfig,
    ServiceEndpointConfig,
    ServiceEndpointHealthMonitorConfig,
    ServiceEndpointProtocol,
)
from zenml.zen_server.deploy.base_provider import BaseServerProvider
from zenml.zen_server.deploy.deployment import ServerDeploymentConfig
from zenml.zen_server.deploy.docker.docker_zen_server import (
    DOCKER_ZENML_SERVER_DEFAULT_TIMEOUT,
    ZEN_SERVER_HEALTHCHECK_URL_PATH,
    DockerServerDeploymentConfig,
    DockerZenServer,
    DockerZenServerConfig,
)

logger = get_logger(__name__)


class DockerServerProvider(BaseServerProvider):
    """Docker ZenML server provider."""

    TYPE: ClassVar[ServerProviderType] = ServerProviderType.DOCKER
    CONFIG_TYPE: ClassVar[
        Type[ServerDeploymentConfig]
    ] = DockerServerDeploymentConfig

    @classmethod
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
        assert isinstance(server_config, DockerServerDeploymentConfig)

        return (
            DockerZenServerConfig(
                root_runtime_path=DockerZenServer.config_path(),
                singleton=True,
                image=server_config.image,
                name=server_config.name,
                server=server_config,
            ),
            ContainerServiceEndpointConfig(
                protocol=ServiceEndpointProtocol.HTTP,
                port=server_config.port,
                allocate_port=False,
            ),
            HTTPEndpointHealthMonitorConfig(
                healthcheck_uri_path=ZEN_SERVER_HEALTHCHECK_URL_PATH,
                use_head_request=True,
            ),
        )

    def _create_service(
        self,
        config: ServerDeploymentConfig,
        timeout: Optional[int] = None,
    ) -> BaseService:
        """Create, start and return the docker ZenML server deployment service.

        Args:
            config: The server deployment configuration.
            timeout: The timeout in seconds to wait until the service is
                running.

        Returns:
            The service instance.

        Raises:
            RuntimeError: If a docker service is already running.
        """
        assert isinstance(config, DockerServerDeploymentConfig)

        if timeout is None:
            timeout = DOCKER_ZENML_SERVER_DEFAULT_TIMEOUT

        service = DockerZenServer.get_service()
        existing_service = DockerZenServer.get_service()
        if existing_service:
            raise RuntimeError(
                f"A docker ZenML server with name '{existing_service.config.name}' "
                f"is already running. Please stop it first before starting a "
                f"new one."
            )

        (
            service_config,
            endpoint_cfg,
            monitor_cfg,
        ) = self._get_service_configuration(config)
        endpoint = ContainerServiceEndpoint(
            config=endpoint_cfg,
            monitor=HTTPEndpointHealthMonitor(
                config=monitor_cfg,
            ),
        )
        service = DockerZenServer(config=service_config, endpoint=endpoint)

        service.start(timeout=timeout)
        return service

    def _update_service(
        self,
        service: BaseService,
        config: ServerDeploymentConfig,
        timeout: Optional[int] = None,
    ) -> BaseService:
        """Update the docker ZenML server deployment service.

        Args:
            service: The service instance.
            config: The new server deployment configuration.
            timeout: The timeout in seconds to wait until the updated service is
                running.

        Returns:
            The updated service instance.
        """
        if timeout is None:
            timeout = DOCKER_ZENML_SERVER_DEFAULT_TIMEOUT

        (
            new_config,
            new_endpoint_cfg,
            new_monitor_cfg,
        ) = self._get_service_configuration(config)

        assert service.endpoint
        assert service.endpoint.monitor

        service.stop(timeout=timeout)
        (
            service.config,
            service.endpoint.config,
            service.endpoint.monitor.config,
        ) = (
            new_config,
            new_endpoint_cfg,
            new_monitor_cfg,
        )
        service.start(timeout=timeout)

        return service

    def _start_service(
        self,
        service: BaseService,
        timeout: Optional[int] = None,
    ) -> BaseService:
        """Start the docker ZenML server deployment service.

        Args:
            service: The service instance.
            timeout: The timeout in seconds to wait until the service is
                running.

        Returns:
            The updated service instance.
        """
        if timeout is None:
            timeout = DOCKER_ZENML_SERVER_DEFAULT_TIMEOUT

        service.start(timeout=timeout)
        return service

    def _stop_service(
        self,
        service: BaseService,
        timeout: Optional[int] = None,
    ) -> BaseService:
        """Stop the docker ZenML server deployment service.

        Args:
            service: The service instance.
            timeout: The timeout in seconds to wait until the service is
                stopped.

        Returns:
            The updated service instance.
        """
        if timeout is None:
            timeout = DOCKER_ZENML_SERVER_DEFAULT_TIMEOUT

        service.stop(timeout=timeout)
        return service

    def _delete_service(
        self,
        service: BaseService,
        timeout: Optional[int] = None,
    ) -> None:
        """Remove the docker ZenML server deployment service.

        Args:
            service: The service instance.
            timeout: The timeout in seconds to wait until the service is
                removed.
        """
        assert isinstance(service, DockerZenServer)

        if timeout is None:
            timeout = DOCKER_ZENML_SERVER_DEFAULT_TIMEOUT

        service.stop(timeout)
        shutil.rmtree(DockerZenServer.config_path())

    def _get_service(self, server_name: str) -> BaseService:
        """Get the docker ZenML server deployment service.

        Args:
            server_name: The server deployment name.

        Returns:
            The service instance.

        Raises:
            KeyError: If the server deployment is not found.
        """
        service = DockerZenServer.get_service()
        if service is None:
            raise KeyError("The docker ZenML server is not deployed.")

        if service.config.name != server_name:
            raise KeyError(
                "The docker ZenML server is deployed but with a different name."
            )

        return service

    def _list_services(self) -> List[BaseService]:
        """Get all service instances for all deployed ZenML servers.

        Returns:
            A list of service instances.
        """
        service = DockerZenServer.get_service()
        if service:
            return [service]
        return []

    def _get_deployment_config(
        self, service: BaseService
    ) -> ServerDeploymentConfig:
        """Recreate the server deployment configuration from a service instance.

        Args:
            service: The service instance.

        Returns:
            The server deployment configuration.
        """
        server = cast(DockerZenServer, service)
        return server.config.server


DockerServerProvider.register_as_provider()
