import subprocess
from typing import TYPE_CHECKING, Any, Dict, Optional, Union

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

ZEN_SERVICE_URL_PATH = "invocations"
ZEN_SERVICE_HEALTHCHECK_URL_PATH = "ping"


class ZenServiceDeploymentEndpointConfig(LocalDaemonServiceEndpointConfig):
    """MLflow daemon service endpoint configuration.

    Attributes:
        zen_service_uri_path: URI subpath for prediction requests
    """

    zen_service_uri_path: str


class ZenServiceDeploymentEndpoint(LocalDaemonServiceEndpoint):
    """A service endpoint exposed by the MLflow deployment daemon.

    Attributes:
        config: service endpoint configuration
        monitor: optional service endpoint health monitor
    """

    config: ZenServiceDeploymentEndpointConfig
    monitor: HTTPEndpointHealthMonitor

    @property
    def endpoint_uri(self) -> Optional[str]:
        uri = self.status.uri
        if not uri:
            return None
        return f"{uri}{self.config.zen_service_uri_path}"


class ZenServiceDeploymentConfig(LocalDaemonServiceConfig):
    """MLflow model deployment configuration.

    Attributes:
        workers: number of workers to use for the service
    """

    port: int = 5555


class ZenServiceDeploymentService(LocalDaemonService):
    """ZenService deployment service that can be used to start a local
    ZenService server

    Attributes:
        SERVICE_TYPE: a service type descriptor with information describing
            the ZenService deployment service class
        config: service configuration
        endpoint: optional service endpoint
    """

    SERVICE_TYPE = ServiceType(
        name="zen_service-deployment",
        type="local",
        flavor="zenml",
        description="ZenService to manage stacks, user and pipelines",
    )

    config: ZenServiceDeploymentConfig
    endpoint: ZenServiceDeploymentEndpoint

    def __init__(
            self,
            config: Union[ZenServiceDeploymentConfig, Dict[str, Any]],
            **attrs: Any,
    ) -> None:
        # ensure that the endpoint is created before the service is initialized
        if (
                isinstance(config, ZenServiceDeploymentConfig)
                and "endpoint" not in attrs
        ):

            endpoint_uri_path = ZEN_SERVICE_URL_PATH
            healthcheck_uri_path = ZEN_SERVICE_HEALTHCHECK_URL_PATH
            use_head_request = True

            endpoint = ZenServiceDeploymentEndpoint(
                config=ZenServiceDeploymentEndpointConfig(
                    protocol=ServiceEndpointProtocol.HTTP,
                    endpoint_uri=endpoint_uri_path,
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
            subprocess.check_output(["uvicorn",
                                     "dummy_fast_api:app",
                                     "--host 0.0.0.0",
                                     f"--port {self.config.port}",
                                     "--reload"])
        except KeyboardInterrupt:
            logger.info(
                "Zen service stopped. Resuming normal execution."
            )

    @property
    def zen_service_uri(self) -> Optional[str]:
        """Get the URI where the prediction service is answering requests.

        Returns:
            The URI where the prediction service can be contacted to process
            HTTP/REST inference requests, or None, if the service isn't running.
        """
        if not self.is_running:
            return None
        return self.endpoint.prediction_uri
