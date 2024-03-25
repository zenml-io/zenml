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
"""Zen Server local provider implementation."""

import shutil
from typing import ClassVar, List, Optional, Tuple, Type, cast
from uuid import uuid4

from zenml import __version__
from zenml.enums import ServerProviderType
from zenml.logger import get_logger
from zenml.services import (
    BaseService,
    HTTPEndpointHealthMonitor,
    HTTPEndpointHealthMonitorConfig,
    LocalDaemonServiceEndpoint,
    LocalDaemonServiceEndpointConfig,
    ServiceConfig,
    ServiceEndpointConfig,
    ServiceEndpointHealthMonitorConfig,
    ServiceEndpointProtocol,
)
from zenml.zen_server.deploy.base_provider import BaseServerProvider
from zenml.zen_server.deploy.deployment import ServerDeploymentConfig
from zenml.zen_server.deploy.local.local_zen_server import (
    LOCAL_ZENML_SERVER_DEFAULT_TIMEOUT,
    ZEN_SERVER_HEALTHCHECK_URL_PATH,
    LocalServerDeploymentConfig,
    LocalZenServer,
    LocalZenServerConfig,
)

logger = get_logger(__name__)


class LocalServerProvider(BaseServerProvider):
    """Local ZenML server provider."""

    TYPE: ClassVar[ServerProviderType] = ServerProviderType.LOCAL
    CONFIG_TYPE: ClassVar[Type[ServerDeploymentConfig]] = (
        LocalServerDeploymentConfig
    )

    @staticmethod
    def check_local_server_dependencies() -> None:
        """Check if local server dependencies are installed.

        Raises:
            RuntimeError: If the dependencies are not installed.
        """
        try:
            # Make sure the ZenML Server dependencies are installed
            import fastapi  # noqa
            import fastapi_utils  # noqa
            import jwt  # noqa
            import multipart  # noqa
            import uvicorn  # noqa
        except ImportError:
            # Unable to import the ZenML Server dependencies.
            raise RuntimeError(
                "The local ZenML server provider is unavailable because the "
                "ZenML server requirements seems to be unavailable on your machine. "
                "This is probably because ZenML was installed without the optional "
                "ZenML Server dependencies. To install the missing dependencies "
                f'run `pip install "zenml[server]=={__version__}"`.'
            )

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
        assert isinstance(server_config, LocalServerDeploymentConfig)
        return (
            LocalZenServerConfig(
                root_runtime_path=LocalZenServer.config_path(),
                singleton=True,
                name=server_config.name,
                blocking=server_config.blocking,
                server=server_config,
            ),
            LocalDaemonServiceEndpointConfig(
                protocol=ServiceEndpointProtocol.HTTP,
                ip_address=str(server_config.ip_address),
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
        """Create, start and return the local ZenML server deployment service.

        Args:
            config: The server deployment configuration.
            timeout: The timeout in seconds to wait until the service is
                running.

        Returns:
            The service instance.

        Raises:
            RuntimeError: If a local service is already running.
        """
        assert isinstance(config, LocalServerDeploymentConfig)

        if timeout is None:
            timeout = LOCAL_ZENML_SERVER_DEFAULT_TIMEOUT

        self.check_local_server_dependencies()
        existing_service = LocalZenServer.get_service()
        if existing_service:
            raise RuntimeError(
                f"A local ZenML server with name '{existing_service.config.name}' "
                f"is already running. Please stop it first before starting a "
                f"new one."
            )

        (
            service_config,
            endpoint_cfg,
            monitor_cfg,
        ) = self._get_service_configuration(config)
        endpoint = LocalDaemonServiceEndpoint(
            config=endpoint_cfg,
            monitor=HTTPEndpointHealthMonitor(
                config=monitor_cfg,
            ),
        )
        service = LocalZenServer(
            uuid=uuid4(), config=service_config, endpoint=endpoint
        )
        service.start(timeout=timeout)
        return service

    def _update_service(
        self,
        service: BaseService,
        config: ServerDeploymentConfig,
        timeout: Optional[int] = None,
    ) -> BaseService:
        """Update the local ZenML server deployment service.

        Args:
            service: The service instance.
            config: The new server deployment configuration.
            timeout: The timeout in seconds to wait until the updated service is
                running.

        Returns:
            The updated service instance.
        """
        if timeout is None:
            timeout = LOCAL_ZENML_SERVER_DEFAULT_TIMEOUT

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
        """Start the local ZenML server deployment service.

        Args:
            service: The service instance.
            timeout: The timeout in seconds to wait until the service is
                running.

        Returns:
            The updated service instance.
        """
        if timeout is None:
            timeout = LOCAL_ZENML_SERVER_DEFAULT_TIMEOUT

        service.start(timeout=timeout)
        return service

    def _stop_service(
        self,
        service: BaseService,
        timeout: Optional[int] = None,
    ) -> BaseService:
        """Stop the local ZenML server deployment service.

        Args:
            service: The service instance.
            timeout: The timeout in seconds to wait until the service is
                stopped.

        Returns:
            The updated service instance.
        """
        if timeout is None:
            timeout = LOCAL_ZENML_SERVER_DEFAULT_TIMEOUT

        service.stop(timeout=timeout)
        return service

    def _delete_service(
        self,
        service: BaseService,
        timeout: Optional[int] = None,
    ) -> None:
        """Remove the local ZenML server deployment service.

        Args:
            service: The service instance.
            timeout: The timeout in seconds to wait until the service is
                removed.
        """
        assert isinstance(service, LocalZenServer)

        if timeout is None:
            timeout = LOCAL_ZENML_SERVER_DEFAULT_TIMEOUT

        service.stop(timeout)
        shutil.rmtree(LocalZenServer.config_path())

    def _get_service(self, server_name: str) -> BaseService:
        """Get the local ZenML server deployment service.

        Args:
            server_name: The server deployment name.

        Returns:
            The service instance.

        Raises:
            KeyError: If the server deployment is not found.
        """
        service = LocalZenServer.get_service()
        if service is None:
            raise KeyError("The local ZenML server is not deployed.")

        if service.config.name != server_name:
            raise KeyError(
                "The local ZenML server is deployed but with a different name."
            )

        return service

    def _list_services(self) -> List[BaseService]:
        """Get all service instances for all deployed ZenML servers.

        Returns:
            A list of service instances.
        """
        service = LocalZenServer.get_service()
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
        server = cast(LocalZenServer, service)
        return server.config.server


LocalServerProvider.register_as_provider()
