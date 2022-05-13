import os
from typing import Any, Dict, Optional, Union

import uvicorn  # type: ignore[import]
from pydantic import Field

from zenml.config.profile_config import ProfileConfiguration
from zenml.constants import (
    ENV_ZENML_PROFILE_NAME,
    ZEN_SERVER_ENTRYPOINT,
    ZEN_SERVER_IP,
)
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

ZEN_SERVER_URL_PATH = ""
ZEN_SERVER_HEALTHCHECK_URL_PATH = "health"


class ZenServerEndpointConfig(LocalDaemonServiceEndpointConfig):
    """ZenServer endpoint configuration.

    Attributes:
        zen_server_uri_path: URI path for the zenml service
    """

    zen_server_uri_path: str


class ZenServerEndpoint(LocalDaemonServiceEndpoint):
    """A service endpoint exposed by the ZenServer daemon.

    Attributes:
        config: service endpoint configuration
        monitor: optional service endpoint health monitor
    """

    config: ZenServerEndpointConfig
    monitor: HTTPEndpointHealthMonitor

    @property
    def endpoint_uri(self) -> Optional[str]:
        uri = self.status.uri
        if not uri:
            return None
        return f"{uri}{self.config.zen_server_uri_path}"


class ZenServerConfig(LocalDaemonServiceConfig):
    """ZenServer deployment configuration.

    Attributes:
        port: Port at which the service responisble for ZenServer is running
        store_profile_configuration: ProfileConfiguration describing where
            the service should persist its data.
    """

    port: int = 8000
    store_profile_configuration: ProfileConfiguration = Field(
        default_factory=lambda: Repository().active_profile
    )


class ZenServer(LocalDaemonService):
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

    config: ZenServerConfig
    endpoint: ZenServerEndpoint

    def __init__(
        self,
        config: Union[ZenServerConfig, Dict[str, Any]],
        **attrs: Any,
    ) -> None:
        # ensure that the endpoint is created before the service is initialized
        if isinstance(config, ZenServerConfig) and "endpoint" not in attrs:

            endpoint_uri_path = ZEN_SERVER_URL_PATH
            healthcheck_uri_path = ZEN_SERVER_HEALTHCHECK_URL_PATH
            use_head_request = True

            endpoint = ZenServerEndpoint(
                config=ZenServerEndpointConfig(
                    protocol=ServiceEndpointProtocol.HTTP,
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
        if self.config.store_profile_configuration.store_type == StoreType.REST:
            raise ValueError(
                "Service cannot be started with REST store type. Make sure you "
                "specify a profile with a non-networked persistence backend "
                "when trying to start the ZenServer. (use command line flag "
                "`--profile=$PROFILE_NAME` or set the env variable "
                f"{ENV_ZENML_PROFILE_NAME} to specify the use of a profile "
                "other than the currently active one)"
            )
        logger.info(
            "Starting ZenServer as blocking "
            "process... press CTRL+C once to stop it."
        )

        self.endpoint.prepare_for_start()

        # this is the only way to pass information into the FastAPI app??
        os.environ[
            "ZENML_PROFILE_CONFIGURATION"
        ] = self.config.store_profile_configuration.json()

        try:
            uvicorn.run(
                ZEN_SERVER_ENTRYPOINT,
                host=ZEN_SERVER_IP,
                port=self.endpoint.status.port,
                log_level="info",
            )
        except KeyboardInterrupt:
            logger.info("ZenServer stopped. Resuming normal execution.")

    @property
    def zen_server_uri(self) -> Optional[str]:
        """Get the URI where the service responsible for ZenServer is running.

        Returns:
            The URI where the service can be contacted for requests,
             or None, if the service isn't running.
        """
        if not self.is_running:
            return None
        return self.endpoint.endpoint_uri
