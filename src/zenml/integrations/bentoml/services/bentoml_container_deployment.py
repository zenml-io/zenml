#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Implementation for the BentoML container deployment service."""

import os
import sys
from typing import Any, Dict, List, Optional, Union

import bentoml
import docker.errors as docker_errors
from bentoml.client import Client

from zenml.client import Client as ZenMLClient
from zenml.constants import DEFAULT_LOCAL_SERVICE_IP_ADDRESS
from zenml.integrations.bentoml.constants import (
    BENTOML_DEFAULT_PORT,
    BENTOML_HEALTHCHECK_URL_PATH,
    BENTOML_PREDICTION_URL_PATH,
)
from zenml.logger import get_logger
from zenml.services.container.container_service import (
    ContainerService,
    ContainerServiceConfig,
)
from zenml.services.container.container_service_endpoint import (
    ContainerServiceEndpoint,
    ContainerServiceEndpointConfig,
)
from zenml.services.service import BaseDeploymentService
from zenml.services.service_endpoint import ServiceEndpointProtocol
from zenml.services.service_monitor import (
    HTTPEndpointHealthMonitor,
    HTTPEndpointHealthMonitorConfig,
)
from zenml.services.service_status import ServiceState
from zenml.services.service_type import ServiceType

logger = get_logger(__name__)


class BentoMLContainerDeploymentConfig(ContainerServiceConfig):
    """BentoML container deployment configuration."""

    model_name: str
    model_uri: str
    bento_tag: str
    bento_uri: Optional[str] = None
    platform: Optional[str] = None
    image: str = ""
    image_tag: Optional[str] = None
    features: Optional[List[str]] = None
    file: Optional[str] = None
    apis: List[str] = []
    working_dir: Optional[str] = None
    workers: int = 1
    backlog: int = 2048
    host: Optional[str] = None
    port: Optional[int] = None


class BentoMLContainerDeploymentEndpointConfig(ContainerServiceEndpointConfig):
    """BentoML container deployment service configuration.

    Attributes:
        prediction_url_path: URI subpath for prediction requests
    """

    prediction_url_path: str


class BentoMLContainerDeploymentEndpoint(ContainerServiceEndpoint):
    """A service endpoint exposed by the BentoML container deployment service.

    Attributes:
        config: service endpoint configuration
    """

    config: BentoMLContainerDeploymentEndpointConfig

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


class BentoMLContainerDeploymentService(
    ContainerService, BaseDeploymentService
):
    """BentoML container deployment service."""

    SERVICE_TYPE = ServiceType(
        name="bentoml-container-deployment",
        type="model-serving",
        flavor="bentoml",
        description="BentoML container prediction service",
        logo_url="https://public-flavor-logos.s3.eu-central-1.amazonaws.com/model_deployer/bentoml.png",
    )

    config: BentoMLContainerDeploymentConfig
    endpoint: BentoMLContainerDeploymentEndpoint

    def __init__(
        self,
        config: Union[BentoMLContainerDeploymentConfig, Dict[str, Any]],
        **attrs: Any,
    ) -> None:
        """Initialize the BentoML deployment service.

        Args:
            config: service configuration
            attrs: additional attributes to set on the service
        """
        # ensure that the endpoint is created before the service is initialized
        # TODO [ENG-700]: implement a service factory or builder for BentoML
        #   deployment services
        if (
            isinstance(config, BentoMLContainerDeploymentConfig)
            and "endpoint" not in attrs
        ):
            endpoint = BentoMLContainerDeploymentEndpoint(
                config=BentoMLContainerDeploymentEndpointConfig(
                    protocol=ServiceEndpointProtocol.HTTP,
                    port=config.port or BENTOML_DEFAULT_PORT,
                    ip_address=config.host or DEFAULT_LOCAL_SERVICE_IP_ADDRESS,
                    prediction_url_path=BENTOML_PREDICTION_URL_PATH,
                ),
                monitor=HTTPEndpointHealthMonitor(
                    config=HTTPEndpointHealthMonitorConfig(
                        healthcheck_uri_path=BENTOML_HEALTHCHECK_URL_PATH,
                    )
                ),
            )
            attrs["endpoint"] = endpoint
        super().__init__(config=config, **attrs)

    # override the is_running property to check if the bentoml container is running
    @property
    def is_running(self) -> bool:
        """Check if the service is currently running.

        This method will actively poll the external service to get its status
        and will return the result.

        Returns:
            True if the service is running and active (i.e. the endpoints are
            responsive, if any are configured), otherwise False.
        """
        self.update_status()
        return self.status.state == ServiceState.ACTIVE

    # override the container start method to use the root user
    def _start_container(self) -> None:
        """Start the service docker container associated with this service."""
        container = self.container

        if container:
            # the container exists, check if it is running
            if container.status == "running":
                logger.debug(
                    "Container for service '%s' is already running",
                    self,
                )
                return

            # the container is stopped or in an error state, remove it
            logger.debug(
                "Removing previous container for service '%s'",
                self,
            )
            container.remove(force=True)

        logger.debug("Starting container for service '%s'...", self)

        try:
            self.docker_client.images.get(self.config.image)
        except docker_errors.ImageNotFound:
            logger.debug(
                "Pulling container image '%s' for service '%s'...",
                self.config.image,
                self,
            )
            self.docker_client.images.pull(self.config.image)

        self._setup_runtime_path()

        ports: Dict[int, Optional[int]] = {}
        if self.endpoint:
            self.endpoint.prepare_for_start()
            if self.endpoint.status.port:
                ports[self.endpoint.status.port] = self.endpoint.status.port

        command, env = self._get_container_cmd()
        volumes = self._get_container_volumes()

        try:
            container = self.docker_client.containers.run(
                name=self.container_id,
                image=self.config.image,
                entrypoint=command,
                detach=True,
                volumes=volumes,
                environment=env,
                remove=False,
                auto_remove=False,
                ports=ports,
                user="root",
                labels={
                    "zenml-service-uuid": str(self.uuid),
                },
                working_dir="/home/bentoml/bento",
                extra_hosts={"host.docker.internal": "host-gateway"},
            )

            logger.debug(
                "Docker container for service '%s' started with ID: %s",
                self,
                self.container_id,
            )
        except docker_errors.DockerException as e:
            logger.error(
                "Docker container for service '%s' failed to start: %s",
                self,
                e,
            )

    def _containerize_and_push_bento(self) -> None:
        """Containerize the bento and push it to the container registry.

        Raises:
            Exception: If the bento containerization fails.
        """
        zenml_client = ZenMLClient()
        container_registry = zenml_client.active_stack.container_registry
        # a tuple of config image and image tag
        if self.config.image and self.config.image_tag:
            image_tag = (self.config.image, self.config.image_tag)
        else:
            # if container registry is present in the stack, name the image
            # with the container registry uri, else name the image with the bento tag
            if container_registry:
                image_name = (
                    f"{container_registry.config.uri}/{self.config.bento_tag}"
                )
                image_tag = (image_name,)  # type: ignore
                self.config.image = image_name
            else:
                # bentoml will use the bento tag as the name of the image
                image_tag = (self.config.bento_tag,)  # type: ignore
                self.config.image = self.config.bento_tag
        try:
            bentoml.container.build(
                bento_tag=self.config.bento_tag,
                backend="docker",  # hardcoding docker since container service only supports docker
                image_tag=image_tag,
                features=self.config.features,
                file=self.config.file,
                platform=self.config.platform,
            )

        except Exception as e:
            logger.error(f"Error containerizing the bento: {e}")
            raise e

        if container_registry:
            logger.info(
                f"Pushing bento to container registry {container_registry.config.uri}"
            )
            # push the bento to the image registry
            container_registry.push_image(self.config.image)
        else:
            logger.warning(
                "No container registry found in the active stack. "
                "Please add a container registry to your stack to push "
                "the bento to an image registry."
            )

    def provision(self) -> None:
        """Provision the service."""
        # containerize the bento
        self._containerize_and_push_bento()
        # run the container
        super().provision()

    def run(self) -> None:
        """Start the service.

        Raises:
            FileNotFoundError: If the bento file is not found.
            subprocess.CalledProcessError: If the bentoml serve command fails.
        """
        from bentoml._internal.service.loader import load

        logger.info("Starting BentoML container deployment service...")

        self.endpoint.prepare_for_start()

        if self.config.working_dir is None:
            if os.path.isdir(os.path.expanduser(self.config.bento_tag)):
                self.config.working_dir = os.path.expanduser(
                    self.config.bento_tag
                )
            else:
                self.config.working_dir = "."
        if sys.path[0] != self.config.working_dir:
            sys.path.insert(0, self.config.working_dir)

        _ = load(bento_identifier=".", working_dir=self.config.working_dir)
        # run bentoml serve command inside the container
        # Use subprocess for better control and error handling
        import subprocess

        try:
            subprocess.run(["bentoml", "serve"], check=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to start BentoML service: {e}")
            raise
        except FileNotFoundError:
            logger.error(
                "BentoML command not found. Make sure it's installed and in the PATH."
            )
            raise

    @property
    def prediction_url(self) -> Optional[str]:
        """Get the URI where the http server is running.

        Returns:
            The URI where the http service can be accessed to get more information
            about the service and to make predictions.
        """
        if not self.is_running:
            return None
        return self.endpoint.prediction_url

    @property
    def prediction_apis_urls(self) -> Optional[List[str]]:
        """Get the URI where the prediction api services is answering requests.

        Returns:
            The URI where the prediction service apis can be contacted to process
            HTTP/REST inference requests, or None, if the service isn't running.
        """
        if not self.is_running:
            return None

        if self.config.apis:
            return [
                f"{self.endpoint.prediction_url}/{api}"
                for api in self.config.apis
            ]
        return None

    def predict(self, api_endpoint: str, data: Any) -> Any:
        """Make a prediction using the service.

        Args:
            data: data to make a prediction on
            api_endpoint: the api endpoint to make the prediction on

        Returns:
            The prediction result.

        Raises:
            Exception: if the service is not running
            ValueError: if the prediction endpoint is unknown.
        """
        if not self.is_running:
            raise Exception(
                "BentoML prediction service is not running. "
                "Please start the service before making predictions."
            )
        if self.endpoint.prediction_url is not None:
            client = Client.from_url(
                self.endpoint.prediction_url.replace("http://", "").rstrip("/")
            )
            result = client.call(api_endpoint, data)
        else:
            raise ValueError("No endpoint known for prediction.")
        return result
