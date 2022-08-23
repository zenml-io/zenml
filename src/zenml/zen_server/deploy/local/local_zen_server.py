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
"""Zen Server implementation."""

import os
from typing import Any, Dict, Optional, Union

import uvicorn
from zenml.config.global_config import GlobalConfiguration  # type: ignore[import]

from zenml.constants import (
    DEFAULT_LOCAL_SERVICE_IP_ADDRESS,
    ENV_ZENML_CONFIG_PATH,
    ZEN_SERVER_ENTRYPOINT,
)
from zenml.enums import StoreType
from zenml.logger import get_logger
from zenml.services import (
    HTTPEndpointHealthMonitor,
    HTTPEndpointHealthMonitorConfig,
    LocalDaemonService,
    LocalDaemonServiceConfig,
    LocalDaemonServiceEndpoint,
    LocalDaemonServiceEndpointConfig,
    ServiceEndpointProtocol,
    ServiceType,
)

logger = get_logger(__name__)

ZEN_SERVER_URL_PATH = ""
ZEN_SERVER_HEALTHCHECK_URL_PATH = "health"


class LocalZenServerEndpointConfig(LocalDaemonServiceEndpointConfig):
    """ZenServer endpoint configuration.

    Attributes:
        zen_server_uri_path: URI path for the ZenServer
    """

    zen_server_uri_path: str


class LocalZenServerEndpoint(LocalDaemonServiceEndpoint):
    """A service endpoint exposed by the ZenServer daemon.

    Attributes:
        config: service endpoint configuration
        monitor: optional service endpoint health monitor
    """

    config: LocalZenServerEndpointConfig
    monitor: HTTPEndpointHealthMonitor

    @property
    def endpoint_uri(self) -> Optional[str]:
        """Return the endpoint URI.

        Returns:
            The endpoint URI or None if the endpoint is not available.
        """
        uri = self.status.uri
        if not uri:
            return None
        return f"{uri}{self.config.zen_server_uri_path}"


class LocalZenServerConfig(LocalDaemonServiceConfig):
    """Local ZenMl server deployment configuration.

    Attributes:
        ip_address: The IP address where the ZenServer will listen for
            connections
        port: Port at which the the ZenServer is accepting connections
    """

    ip_address: str = DEFAULT_LOCAL_SERVICE_IP_ADDRESS
    port: int = 8000


class LocalZenServer(LocalDaemonService):
    """Service daemon that can be used to start a local ZenServer.

    Attributes:
        config: service configuration
        endpoint: optional service endpoint
    """

    SERVICE_TYPE = ServiceType(
        name="zen_server",
        type="zenml",
        flavor="zenml",
        description="ZenServer to manage stacks, users and pipelines",
    )

    config: LocalZenServerConfig
    endpoint: LocalZenServerEndpoint

    def __init__(
        self,
        config: Union[LocalZenServerConfig, Dict[str, Any]],
        **attrs: Any,
    ) -> None:
        """Initialize the ZenServer.

        Args:
            config: service configuration.
            attrs: additional attributes.
        """
        # ensure that the endpoint is created before the service is initialized
        if isinstance(config, LocalZenServerConfig) and "endpoint" not in attrs:

            endpoint_uri_path = ZEN_SERVER_URL_PATH
            healthcheck_uri_path = ZEN_SERVER_HEALTHCHECK_URL_PATH
            use_head_request = True

            endpoint = LocalZenServerEndpoint(
                config=LocalZenServerEndpointConfig(
                    protocol=ServiceEndpointProtocol.HTTP,
                    ip_address=config.ip_address,
                    port=config.port,
                    zen_server_uri_path=endpoint_uri_path,
                ),
                monitor=HTTPEndpointHealthMonitor(
                    config=HTTPEndpointHealthMonitorConfig(
                        healthcheck_uri_path=healthcheck_uri_path,
                        use_head_request=use_head_request,
                    )
                ),
            )
            attrs["endpoint"] = endpoint
        super().__init__(config=config, **attrs)

    def run(self) -> None:
        """Run the ZenServer.

        Raises:
            ValueError: if started with a global configuration that connects to
            another ZenML server.
        """
        gc = GlobalConfiguration()
        if gc.store and gc.store.type == StoreType.REST:
            raise ValueError(
                "The ZenML server cannot be started with REST store type."
            )
        logger.info(
            "Starting ZenServer as blocking "
            "process... press CTRL+C once to stop it."
        )

        self.endpoint.prepare_for_start()

        # force the server to use its dedicated global configuration path
        os.environ[ENV_ZENML_CONFIG_PATH] = os.path.join(
            self.config.root_runtime_path, ".zenconfig"
        )

        try:
            uvicorn.run(
                ZEN_SERVER_ENTRYPOINT,
                host=self.config.ip_address,
                port=self.endpoint.status.port,
                log_level="info",
            )
        except KeyboardInterrupt:
            logger.info("ZenServer stopped. Resuming normal execution.")

    @property
    def zen_server_uri(self) -> Optional[str]:
        """Get the URI where the service responsible for the ZenServer is running.

        Returns:
            The URI where the service can be contacted for requests,
                or None, if the service isn't running.
        """
        if not self.is_running:
            return None
        return self.endpoint.endpoint_uri

    def update(self, config: LocalZenServerConfig) -> None:
        """Update the ZenServer configuration.

        Args:
            config: new server configuration.
        """
        super().update(config)
        self.endpoint.config.ip_address = config.ip_address
        self.endpoint.config.port = config.port
