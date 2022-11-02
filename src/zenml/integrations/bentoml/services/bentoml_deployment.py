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
"""Implementation for the BentoML inference service."""

import json
import os
import re
from typing import TYPE_CHECKING, Any, Dict, Generator, Optional, Tuple, Union
from uuid import UUID

import requests
from pydantic import Field, ValidationError
from zenml.constants import DEFAULT_LOCAL_SERVICE_IP_ADDRESS
from bentoml.serve import serve_http_production
from bentoml._internal.configuration.containers import BentoMLContainer

from zenml import __version__
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

from bentoml.steps import constants
if TYPE_CHECKING:

    from zenml.integrations.kserve.model_deployers.kserve_model_deployer import (  # noqa
        BentoMLModelDeployer,
    )

logger = get_logger(__name__)


BENTOML_DEFAULT_PORT = 3000
BENTOML_HEALTHCHECK_URL_PATH = "readyz"

class BentoMLDeploymentEndpointConfig(LocalDaemonServiceEndpointConfig):
    """BentoML deployment service configuration.

    Attributes:
        prediction_url_path: URI subpath for prediction requests
    """



class BentoMLDeploymentEndpoint(LocalDaemonServiceEndpoint):
    """A service endpoint exposed by the MLflow deployment daemon.

    Attributes:
        config: service endpoint configuration
    """

    config: BentoMLDeploymentEndpointConfig
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
        return os.path.join(uri)

class BentoMLDeploymentConfig(LocalDaemonServiceConfig):
    """MLflow model deployment configuration.

    Attributes:
        model_uri: URI of the MLflow model to serve
        model_name: the name of the model
        workers: number of workers to use for the prediction service
        mlserver: set to True to use the MLflow MLServer backend (see
            https://github.com/SeldonIO/MLServer). If False, the
            MLflow built-in scoring server will be used.
    """

    bento: str
    model_uri: str
    workers: int = BentoMLContainer.api_server_workers.get()
    port: int = BentoMLContainer.http.port.get()
    backlog: int = BentoMLContainer.api_server_config.backlog.get()
    production: bool = False
    work_dir: str = None
    host: str = BentoMLContainer.http.host.get()

class BentoMLDeploymentService(LocalDaemonService):
    """BentoML deployment service used to start a local prediction server for MLflow models.

    Attributes:
        SERVICE_TYPE: a service type descriptor with information describing
            the MLflow deployment service class
        config: service configuration
        endpoint: optional service endpoint
    """

    SERVICE_TYPE = ServiceType(
        name="bentoml-deployment",
        type="model-serving",
        flavor="bentoml",
        description="BentoML prediction service",
    )

    config: BentoMLDeploymentConfig
    endpoint: BentoMLDeploymentEndpoint

    def __init__(
        self,
        config: Union[BentoMLDeploymentConfig, Dict[str, Any]],
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
            isinstance(config, BentoMLDeploymentConfig)
            and "endpoint" not in attrs
        ):
            
            endpoint = BentoMLDeploymentEndpoint(
                config=BentoMLDeploymentEndpointConfig(
                    protocol=ServiceEndpointProtocol.HTTP,
                    port=config.port,
                    ip_address=config.host,
                ),
                monitor=HTTPEndpointHealthMonitor(
                    config=HTTPEndpointHealthMonitorConfig(
                        healthcheck_uri_path=BENTOML_HEALTHCHECK_URL_PATH,
                    )
                ),
            )
            attrs["endpoint"] = endpoint
        super().__init__(config=config, **attrs)

    def run(self) -> None:
        """Start the service."""
        logger.info(
            "Starting MLflow prediction service as blocking "
            "process... press CTRL+C once to stop it."
        )

        self.endpoint.prepare_for_start()
        try:
            if self.config.production:
            
                from bentoml.serve import serve_http_production

                serve_http_production(
                    self.config.bento,
                    port= self.config.port,
                    workers=self.config.api_workers,
                    backlog=self.config.backlog,
                    work_dir=self.config.work_dir,
                    host = self.config.host,
                )
            else:
                from bentoml.serve import serve_http_development

                serve_http_development(
                    self.config.bento,
                    port=self.config.port,
                    workers=self.config.api_workers,
                    work_dir=self.config.work_dir,
                    host=self.config.host,
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

