#  Copyright (c) ZenML GmbH 2022-2023. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Implementation of the MLflow deployment functionality."""

import os
import sys
from typing import TYPE_CHECKING, Any, Dict, Optional, Union

import numpy as np
import pandas as pd
import requests
from mlflow.pyfunc.backend import PyFuncBackend
from mlflow.version import VERSION as MLFLOW_VERSION
from pydantic import field_validator

from zenml.client import Client
from zenml.constants import DEFAULT_SERVICE_START_STOP_TIMEOUT
from zenml.integrations.mlflow.experiment_trackers.mlflow_experiment_tracker import (
    MLFlowExperimentTracker,
)
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
from zenml.services.service import BaseDeploymentService

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
        """Gets the prediction URL for the endpoint.

        Returns:
            the prediction URL for the endpoint
        """
        uri = self.status.uri
        if not uri:
            return None
        return os.path.join(uri, self.config.prediction_url_path)


class MLFlowDeploymentConfig(LocalDaemonServiceConfig):
    """MLflow model deployment configuration.

    Attributes:
        model_uri: URI of the MLflow model to serve
        model_name: the name of the model
        workers: number of workers to use for the prediction service
        registry_model_name: the name of the model in the registry
        registry_model_version: the version of the model in the registry
        mlserver: set to True to use the MLflow MLServer backend (see
            https://github.com/SeldonIO/MLServer). If False, the
            MLflow built-in scoring server will be used.
        timeout: timeout in seconds for starting and stopping the service
    """

    model_uri: str
    model_name: str
    registry_model_name: Optional[str] = None
    registry_model_version: Optional[str] = None
    registry_model_stage: Optional[str] = None
    workers: int = 1
    mlserver: bool = False
    timeout: int = DEFAULT_SERVICE_START_STOP_TIMEOUT

    @field_validator("mlserver")
    @classmethod
    def validate_mlserver_python_version(cls, mlserver: bool) -> bool:
        """Validates the Python version if mlserver is used.

        Args:
            mlserver: set to True if the MLflow MLServer backend is used,
                else set to False and MLflow built-in scoring server will be
                used.

        Returns:
            the validated value

        Raises:
            ValueError: if mlserver is set to true on Python 3.12 as it is not
                yet supported.
        """
        if mlserver is True and sys.version_info.minor >= 12:
            raise ValueError(
                "The mlserver deployment is not yet supported on Python 3.12 "
                "or above."
            )
        return mlserver


class MLFlowDeploymentService(LocalDaemonService, BaseDeploymentService):
    """MLflow deployment service used to start a local prediction server for MLflow models.

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
        logo_url="https://public-flavor-logos.s3.eu-central-1.amazonaws.com/model_deployer/mlflow.png",
    )

    config: MLFlowDeploymentConfig
    endpoint: MLFlowDeploymentEndpoint

    def __init__(
        self,
        config: Union[MLFlowDeploymentConfig, Dict[str, Any]],
        **attrs: Any,
    ) -> None:
        """Initialize the MLflow deployment service.

        Args:
            config: service configuration
            attrs: additional attributes to set on the service
        """
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
        """Start the service.

        Raises:
            ValueError: if the active stack doesn't have an MLflow experiment
                tracker
        """
        logger.info(
            "Starting MLflow prediction service as blocking "
            "process... press CTRL+C once to stop it."
        )

        self.endpoint.prepare_for_start()
        try:
            backend_kwargs: Dict[str, Any] = {}
            serve_kwargs: Dict[str, Any] = {}
            mlflow_version = MLFLOW_VERSION.split(".")
            # MLflow version 1.26 introduces an additional mandatory
            # `timeout` argument to the `PyFuncBackend.serve` function
            if int(mlflow_version[1]) >= 26 or int(mlflow_version[0]) >= 2:
                serve_kwargs["timeout"] = None
            # Mlflow 2.0+ requires the env_manager to be set to "local"
            # to run the deploy the model on the local running environment
            if int(mlflow_version[0]) >= 2:
                backend_kwargs["env_manager"] = "local"
            backend = PyFuncBackend(
                config={},
                no_conda=True,
                workers=self.config.workers,
                install_mlflow=False,
                **backend_kwargs,
            )
            experiment_tracker = Client().active_stack.experiment_tracker
            if not isinstance(experiment_tracker, MLFlowExperimentTracker):
                raise ValueError(
                    "MLflow model deployer step requires an MLflow experiment "
                    "tracker. Please add an MLflow experiment tracker to your "
                    "stack."
                )
            experiment_tracker.configure_mlflow()
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

    def predict(
        self, request: Union["NDArray[Any]", pd.DataFrame]
    ) -> "NDArray[Any]":
        """Make a prediction using the service.

        Args:
            request: a Numpy Array or Pandas DataFrame representing the request

        Returns:
            A numpy array representing the prediction returned by the service.

        Raises:
            Exception: if the service is not running
            ValueError: if the prediction endpoint is unknown.
        """
        if not self.is_running:
            raise Exception(
                "MLflow prediction service is not running. "
                "Please start the service before making predictions."
            )

        if self.endpoint.prediction_url is not None:
            if type(request) is pd.DataFrame:
                response = requests.post(  # nosec
                    self.endpoint.prediction_url,
                    json={"instances": request.to_dict("records")},
                )
            else:
                response = requests.post(  # nosec
                    self.endpoint.prediction_url,
                    json={"instances": request.tolist()},
                )
        else:
            raise ValueError("No endpoint known for prediction.")
        response.raise_for_status()
        if int(MLFLOW_VERSION.split(".")[0]) <= 1:
            return np.array(response.json())
        else:
            # Mlflow 2.0+ returns a dictionary with the predictions
            # under the "predictions" key
            return np.array(response.json()["predictions"])
