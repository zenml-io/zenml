import subprocess
from typing import Any, Dict, Optional, Union

import uvicorn

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

ZEN_SERVICE_URL_PATH = "/"
ZEN_SERVICE_HEALTHCHECK_URL_PATH = "health"


class ZenServiceEndpointConfig(LocalDaemonServiceEndpointConfig):
    """MLflow daemon service endpoint configuration.

    Attributes:
        zen_service_uri_path: URI path for the zenml service
    """

    zen_service_uri_path: str


class ZenServiceEndpoint(LocalDaemonServiceEndpoint):
    """A service endpoint exposed by the MLflow deployment daemon.

    Attributes:
        config: service endpoint configuration
        monitor: optional service endpoint health monitor
    """

    config: ZenServiceEndpointConfig
    monitor: HTTPEndpointHealthMonitor

    @property
    def endpoint_uri(self) -> Optional[str]:
        uri = self.status.uri
        if not uri:
            return None
        return f"{uri}{self.config.zen_service_uri_path}"


class ZenServiceConfig(LocalDaemonServiceConfig):
    """MLflow model deployment configuration.

    Attributes:
        port: Port at which the service is running
    """

    port: int = 8000


class ZenServiceService(LocalDaemonService):
    """ZenService deployment service that can be used to start a local
    ZenService server

    Attributes:
        SERVICE_TYPE: a service type descriptor with information describing
            the ZenService deployment service class
        config: service configuration
        endpoint: optional service endpoint
    """

    SERVICE_TYPE = ServiceType(
        name="zen_service",
        type="zenml",
        flavor="zenml",
        description="ZenService to manage stacks, user and pipelines",
    )

    config: ZenServiceConfig
    endpoint: ZenServiceEndpoint

    def __init__(
            self,
            config: Union[ZenServiceConfig, Dict[str, Any]],
            **attrs: Any,
    ) -> None:
        # ensure that the endpoint is created before the service is initialized
        if (
                isinstance(config, ZenServiceConfig)
                and "endpoint" not in attrs
        ):

            endpoint_uri_path = ZEN_SERVICE_URL_PATH
            healthcheck_uri_path = ZEN_SERVICE_HEALTHCHECK_URL_PATH
            use_head_request = True

            endpoint = ZenServiceEndpoint(
                config=ZenServiceEndpointConfig(
                    protocol=ServiceEndpointProtocol.HTTP,
                    port=config.port,
                    zen_service_uri_path=endpoint_uri_path,
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
        logger.info(
            "Starting ZenService as blocking "
            "process... press CTRL+C once to stop it."
        )

        self.endpoint.prepare_for_start()

        try:
            uvicorn.run(
                "zenml.zervice.dummy_fast_api:app",
                host="127.0.0.1",
                port=self.endpoint.status.port,
                log_level="info")
        except KeyboardInterrupt:
            logger.info(
                "Zen service stopped. Resuming normal execution."
            )

    @property
    def zen_service_uri(self) -> Optional[str]:
        """Get the URI where the service is running.

        Returns:
            The URI where the service can be contacted
            HTTP/REST inference requests, or None, if the service isn't running.
        """
        if not self.is_running:
            return None
        return self.endpoint.endpoint_uri
