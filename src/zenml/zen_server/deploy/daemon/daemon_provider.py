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
"""Zen Server daemon provider implementation."""

import shutil
from typing import ClassVar, Optional, Tuple, Type, cast
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
from zenml.zen_server.deploy.daemon.daemon_zen_server import (
    DAEMON_ZENML_SERVER_DEFAULT_TIMEOUT,
    ZEN_SERVER_HEALTHCHECK_URL_PATH,
    DaemonServerDeploymentConfig,
    DaemonZenServer,
    DaemonZenServerConfig,
)
from zenml.zen_server.deploy.deployment import LocalServerDeploymentConfig

logger = get_logger(__name__)


class DaemonServerProvider(BaseServerProvider):
    """Daemon ZenML server provider."""

    TYPE: ClassVar[ServerProviderType] = ServerProviderType.DAEMON
    CONFIG_TYPE: ClassVar[Type[LocalServerDeploymentConfig]] = (
        DaemonServerDeploymentConfig
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
            import jwt  # noqa
            import multipart  # noqa
            import uvicorn  # noqa
        except ImportError:
            # Unable to import the ZenML Server dependencies.
            raise RuntimeError(
                "The local daemon ZenML server provider is unavailable because the "
                "ZenML server requirements seems to be unavailable on your machine. "
                "This is probably because ZenML was installed without the optional "
                "ZenML Server dependencies. To install the missing dependencies "
                f'run `pip install "zenml[server]=={__version__}"`.'
            )

    @classmethod
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
        assert isinstance(server_config, DaemonServerDeploymentConfig)
        return (
            DaemonZenServerConfig(
                root_runtime_path=DaemonZenServer.config_path(),
                singleton=True,
                name=ServerProviderType.DAEMON.value,
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
        config: LocalServerDeploymentConfig,
        timeout: Optional[int] = None,
    ) -> BaseService:
        """Create, start and return the local daemon ZenML server deployment service.

        Args:
            config: The server deployment configuration.
            timeout: The timeout in seconds to wait until the service is
                running.

        Returns:
            The service instance.

        Raises:
            RuntimeError: If a local service is already running.
        """
        assert isinstance(config, DaemonServerDeploymentConfig)

        if timeout is None:
            timeout = DAEMON_ZENML_SERVER_DEFAULT_TIMEOUT

        self.check_local_server_dependencies()
        existing_service = DaemonZenServer.get_service()
        if existing_service:
            raise RuntimeError(
                f"A local daemon ZenML server with name '{existing_service.config.name}' "
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
        service = DaemonZenServer(
            uuid=uuid4(), config=service_config, endpoint=endpoint
        )
        service.start(timeout=timeout)
        return service

    def _update_service(
        self,
        service: BaseService,
        config: LocalServerDeploymentConfig,
        timeout: Optional[int] = None,
    ) -> BaseService:
        """Update the local daemon ZenML server deployment service.

        Args:
            service: The service instance.
            config: The new server deployment configuration.
            timeout: The timeout in seconds to wait until the updated service is
                running.

        Returns:
            The updated service instance.
        """
        if timeout is None:
            timeout = DAEMON_ZENML_SERVER_DEFAULT_TIMEOUT

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
        """Start the local daemon ZenML server deployment service.

        Args:
            service: The service instance.
            timeout: The timeout in seconds to wait until the service is
                running.

        Returns:
            The updated service instance.
        """
        if timeout is None:
            timeout = DAEMON_ZENML_SERVER_DEFAULT_TIMEOUT

        service.start(timeout=timeout)
        return service

    def _stop_service(
        self,
        service: BaseService,
        timeout: Optional[int] = None,
    ) -> BaseService:
        """Stop the local daemon ZenML server deployment service.

        Args:
            service: The service instance.
            timeout: The timeout in seconds to wait until the service is
                stopped.

        Returns:
            The updated service instance.
        """
        if timeout is None:
            timeout = DAEMON_ZENML_SERVER_DEFAULT_TIMEOUT

        service.stop(timeout=timeout)
        return service

    def _delete_service(
        self,
        service: BaseService,
        timeout: Optional[int] = None,
    ) -> None:
        """Remove the local daemon ZenML server deployment service.

        Args:
            service: The service instance.
            timeout: The timeout in seconds to wait until the service is
                removed.
        """
        assert isinstance(service, DaemonZenServer)

        if timeout is None:
            timeout = DAEMON_ZENML_SERVER_DEFAULT_TIMEOUT

        service.stop(timeout)
        shutil.rmtree(DaemonZenServer.config_path())

    def _get_service(self) -> BaseService:
        """Get the local daemon ZenML server deployment service.

        Returns:
            The service instance.

        Raises:
            KeyError: If the server deployment is not found.
        """
        service = DaemonZenServer.get_service()
        if service is None:
            raise KeyError("The local daemon ZenML server is not deployed.")

        return service

    def _get_deployment_config(
        self, service: BaseService
    ) -> LocalServerDeploymentConfig:
        """Recreate the server deployment configuration from a service instance.

        Args:
            service: The service instance.

        Returns:
            The server deployment configuration.
        """
        server = cast(DaemonZenServer, service)
        return server.config.server


DaemonServerProvider.register_as_provider()
