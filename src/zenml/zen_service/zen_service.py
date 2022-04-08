import os
from typing import Any, Dict, Optional, Union

import uvicorn  # type: ignore[import]
from pydantic import Field

from zenml.config.profile_config import ProfileConfiguration
from zenml.constants import ENV_ZENML_PROFILE_NAME
from zenml.enums import StoreType
from zenml.logger import get_logger
from zenml.repository import Repository
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

ZEN_SERVICE_URL_PATH = ""
ZEN_SERVICE_HEALTHCHECK_URL_PATH = "health"


class ZenServiceEndpointConfig(LocalDaemonServiceEndpointConfig):
    """Zen Service endpoint configuration.

    Attributes:
        zen_service_uri_path: URI path for the zenml service
    """

    zen_service_uri_path: str


class ZenServiceEndpoint(LocalDaemonServiceEndpoint):
    """A service endpoint exposed by the Zen service daemon.

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
    """Zen Service deployment configuration.

    Attributes:
        port: Port at which the service is running
        store_profile_configuration: ProfileConfiguration describing where
            the service should persist its data.
    """

    port: int = 8000
    store_profile_configuration: ProfileConfiguration = Field(
        default_factory=lambda: Repository().active_profile
    )


class ZenService(LocalDaemonService):
    """ZenService daemon that can be used to start a local ZenService server.

    Attributes:
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
        if isinstance(config, ZenServiceConfig) and "endpoint" not in attrs:

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
        if self.config.store_profile_configuration.store_type == StoreType.REST:
            raise ValueError(
                "Service cannot be started with REST store type. Make sure you "
                "specify a profile with a non-networked persistence backend "
                "when trying to start the Zen Service. (use command line flag "
                "`--profile=$PROFILE_NAME` or set the env variable "
                f"{ENV_ZENML_PROFILE_NAME} to specify the use of a profile "
                "other than the currently active one)"
            )
        logger.info(
            "Starting ZenService as blocking "
            "process... press CTRL+C once to stop it."
        )

        self.endpoint.prepare_for_start()

        # this is the only way to pass information into the FastAPI app??
        os.environ[
            "ZENML_PROFILE_CONFIGURATION"
        ] = self.config.store_profile_configuration.json()

        try:
            uvicorn.run(
                "zenml.zen_service.zen_service_api:app",
                host="127.0.0.1",
                port=self.endpoint.status.port,
                log_level="info",
            )
        except KeyboardInterrupt:
            logger.info("Zen service stopped. Resuming normal execution.")

    @property
    def zen_service_uri(self) -> Optional[str]:
        """Get the URI where the service is running.

        Returns:
            The URI where the service can be contacted for requests,
             or None, if the service isn't running.
        """
        if not self.is_running:
            return None
        return self.endpoint.endpoint_uri
