import os
from typing import Any, Dict, Optional, Union

import uvicorn  # type: ignore[import]
from pydantic import Field

from zenml.config.global_config import GlobalConfiguration
from zenml.constants import (
    DEFAULT_LOCAL_SERVICE_IP_ADDRESS,
    ENV_ZENML_PROFILE_NAME,
    ZEN_SERVER_ENTRYPOINT,
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
        zen_server_uri_path: URI path for the ZenServer
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
        ip_address: The IP address where the ZenServer will listen for
            connections
        port: Port at which the the ZenServer is accepting connections
        profile_name: name of the Profile to use to store data.
    """

    ip_address: str = DEFAULT_LOCAL_SERVICE_IP_ADDRESS
    port: int = 8000
    profile_name: str = Field(
        default_factory=lambda: Repository().active_profile_name
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
        profile = GlobalConfiguration().get_profile(self.config.profile_name)
        if profile is None:
            raise ValueError(
                f"Could not find profile with name {self.config.profile_name}."
            )

        if profile.store_type == StoreType.REST:
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
        os.environ["ZENML_PROFILE_NAME"] = self.config.profile_name

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
