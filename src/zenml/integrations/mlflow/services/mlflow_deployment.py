from typing import TYPE_CHECKING, Any, Dict, Optional, Union

import numpy as np
import requests
from mlflow.pyfunc.backend import PyFuncBackend  # type: ignore [import]
from mlflow.version import VERSION as MLFLOW_VERSION  # type: ignore [import]

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

if TYPE_CHECKING:
    from numpy.typing import NDArray

logger = get_logger(__name__)

MLFLOW_PREDICTION_URL_PATH = "invocations"
MLFLOW_HEALTHCHECK_URL_PATH = "ping"

MLSERVER_PREDICTION_URL_PATH = "invocations"
MLSERVER_HEALTHCHECK_URL_PATH = "v2/models/mlflow-model/ready"


class MLFlowDeploymentEndpointConfig(LocalDaemonServiceEndpointConfig):
    """MLflow daemon service endpoint configuration.

    Attributes:
        prediction_url_path: URI subpath for prediction requests
    """

    prediction_url_path: str


class MLFlowDeploymentEndpoint(LocalDaemonServiceEndpoint):
    """A service endpoint exposed by the MLflow deployment daemon.

    Attributes:
        config: service endpoint configuration
        monitor: optional service endpoint health monitor
    """

    config: MLFlowDeploymentEndpointConfig
    monitor: HTTPEndpointHealthMonitor

    @property
    def prediction_url(self) -> Optional[str]:
        uri = self.status.uri
        if not uri:
            return None
        return f"{uri}{self.config.prediction_url_path}"


class MLFlowDeploymentConfig(LocalDaemonServiceConfig):
    """MLflow model deployment configuration.

    Attributes:
        model_uri: URI of the MLflow model to serve
        model_name: the name of the model
        workers: number of workers to use for the prediction service
        mlserver: set to True to use the MLflow MLServer backend (see
            https://github.com/SeldonIO/MLServer). If False, the
            MLflow built-in scoring server will be used.
    """

    model_uri: str
    model_name: str
    workers: int = 1
    mlserver: bool = False


class MLFlowDeploymentService(LocalDaemonService):
    """MLFlow deployment service that can be used to start a local prediction
    server for MLflow models.

    Attributes:
        SERVICE_TYPE: a service type descriptor with information describing
            the MLflow deployment service class
        config: service configuration
        endpoint: optional service endpoint
    """

    SERVICE_TYPE = ServiceType(
        name="mlflow-deployment",
        type="model-serving",
        flavor="mlflow",
        description="MLflow prediction service",
    )

    config: MLFlowDeploymentConfig
    endpoint: MLFlowDeploymentEndpoint

    def __init__(
        self,
        config: Union[MLFlowDeploymentConfig, Dict[str, Any]],
        **attrs: Any,
    ) -> None:
        # ensure that the endpoint is created before the service is initialized
        # TODO [ENG-700]: implement a service factory or builder for MLflow
        #   deployment services
        if (
            isinstance(config, MLFlowDeploymentConfig)
            and "endpoint" not in attrs
        ):
            if config.mlserver:
                prediction_url_path = MLSERVER_PREDICTION_URL_PATH
                healthcheck_uri_path = MLSERVER_HEALTHCHECK_URL_PATH
                use_head_request = False
            else:
                prediction_url_path = MLFLOW_PREDICTION_URL_PATH
                healthcheck_uri_path = MLFLOW_HEALTHCHECK_URL_PATH
                use_head_request = True

            endpoint = MLFlowDeploymentEndpoint(
                config=MLFlowDeploymentEndpointConfig(
                    protocol=ServiceEndpointProtocol.HTTP,
                    prediction_url_path=prediction_url_path,
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
            "Starting MLflow prediction service as blocking "
            "process... press CTRL+C once to stop it."
        )

        self.endpoint.prepare_for_start()

        try:
            serve_kwargs: Dict[str, Any] = {}
            # MLflow version 1.26 introduces an additional mandatory
            # `timeout` argument to the `PyFuncBackend.serve` function
            if int(MLFLOW_VERSION.split(".")[1]) >= 26:
                serve_kwargs["timeout"] = None

            backend = PyFuncBackend(
                config={},
                no_conda=True,
                workers=self.config.workers,
                install_mlflow=False,
            )
            backend.serve(
                model_uri=self.config.model_uri,
                port=self.endpoint.status.port,
                host="localhost",
                enable_mlserver=self.config.mlserver,
                **serve_kwargs,
            )
        except KeyboardInterrupt:
            logger.info(
                "MLflow prediction service stopped. Resuming normal execution."
            )

    @property
    def prediction_url(self) -> Optional[str]:
        """Get the URI where the prediction service is answering requests.

        Returns:
            The URI where the prediction service can be contacted to process
            HTTP/REST inference requests, or None, if the service isn't running.
        """
        if not self.is_running:
            return None
        return self.endpoint.prediction_url

    def predict(self, request: "NDArray[Any]") -> "NDArray[Any]":
        """Make a prediction using the service.

        Args:
            request: a numpy array representing the request

        Returns:
            A numpy array representing the prediction returned by the service.
        """
        if not self.is_running:
            raise Exception(
                "MLflow prediction service is not running. "
                "Please start the service before making predictions."
            )

        if self.endpoint.prediction_url is not None:
            response = requests.post(
                self.endpoint.prediction_url,
                json={"instances": request.tolist()},
            )
        else:
            raise ValueError("No endpoint known for prediction.")
        response.raise_for_status()
        return np.array(response.json())
