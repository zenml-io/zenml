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
"""Implementation of the ZenML local Docker pipeline server.


TODO:

* figure out which image to use for the docker container from the deployment (or
build another ?)
* figure out how to inject the FastAPI/other requirements into the image
* which environment variables go into the container? who provides them?
* how are endpoints authenticated?
* check the health status of the container too
"""

import copy
import os
import sys
from typing import (
    Any,
    Dict,
    Generator,
    List,
    Optional,
    Tuple,
    Type,
    cast,
)

import docker.errors as docker_errors
from docker.client import DockerClient
from docker.models.containers import Container
from pydantic import BaseModel

from zenml.config.base_settings import BaseSettings
from zenml.config.global_config import GlobalConfiguration
from zenml.constants import (
    ENV_ZENML_LOCAL_STORES_PATH,
)
from zenml.enums import PipelineEndpointStatus, StackComponentType
from zenml.logger import get_logger
from zenml.models import (
    PipelineDeploymentResponse,
    PipelineEndpointOperationalState,
    PipelineEndpointResponse,
)
from zenml.pipeline_servers.base_pipeline_server import (
    BasePipelineServer,
    BasePipelineServerConfig,
    BasePipelineServerFlavor,
    PipelineEndpointDeletionError,
    PipelineEndpointDeploymentError,
    PipelineEndpointNotFoundError,
)
from zenml.serving.entrypoint import ServingPipelineEntrypoint
from zenml.stack import Stack, StackValidator
from zenml.utils import docker_utils
from zenml.utils.networking_utils import (
    port_available,
    scan_for_available_port,
)

logger = get_logger(__name__)


class DockerPipelineEndpointMetadata(BaseModel):
    """Metadata for a Docker pipeline endpoint."""

    port: int
    container_id: Optional[str] = None
    container_name: Optional[str] = None
    container_image: Optional[str] = None
    container_status: Optional[str] = None

    @classmethod
    def from_container(
        cls, container: Container
    ) -> "DockerPipelineEndpointMetadata":
        """Create a DockerPipelineEndpointMetadata from a docker container.

        Args:
            container: The docker container to get the metadata for.

        Returns:
            The metadata for the docker container.
        """
        image = container.image
        if image is not None:
            image_url = image.attrs["RepoDigests"][0]
        else:
            image_url = None
        return cls(
            port=container.ports[0][0],
            container_id=container.id,
            container_name=container.name,
            container_image=image_url,
            container_status=container.status,
        )

    @classmethod
    def from_endpoint(
        cls, endpoint: PipelineEndpointResponse
    ) -> "DockerPipelineEndpointMetadata":
        """Create a DockerPipelineEndpointMetadata from a pipeline endpoint.

        Args:
            endpoint: The pipeline endpoint to get the metadata for.

        Returns:
            The metadata for the pipeline endpoint.
        """
        return cls.model_validate(endpoint.endpoint_metadata)


class DockerPipelineServer(BasePipelineServer):
    """Pipeline server responsible for serving pipelines locally using Docker."""

    _docker_client: Optional[DockerClient] = None

    @property
    def settings_class(self) -> Optional[Type["BaseSettings"]]:
        """Settings class for the Local Docker pipeline server.

        Returns:
            The settings class.
        """
        return DockerPipelineServerSettings

    @property
    def config(self) -> "DockerPipelineServerConfig":
        """Returns the `DockerPipelineServerConfig` config.

        Returns:
            The configuration.
        """
        return cast(DockerPipelineServerConfig, self._config)

    @property
    def validator(self) -> Optional[StackValidator]:
        """Ensures there is an image builder in the stack.

        Returns:
            A `StackValidator` instance.
        """
        return StackValidator(
            required_components={StackComponentType.IMAGE_BUILDER}
        )

    @property
    def docker_client(self) -> DockerClient:
        """Initialize and/or return the docker client.

        Returns:
            The docker client.
        """
        if self._docker_client is None:
            self._docker_client = (
                docker_utils._try_get_docker_client_from_env()
            )
        return self._docker_client

    def _lookup_free_port(
        self,
        preferred_ports: List[int] = [],
        allocate_port_if_busy: bool = True,
        range: Tuple[int, int] = (8000, 65535),
    ) -> int:
        """Search for a free TCP port for the Docker pipeline server.

        If a list of preferred TCP port values is explicitly requested, they
        will be checked in order.

        Args:
            preferred_ports: A list of preferred TCP port values.
            allocate_port_if_busy: If True, allocate a free port if the
                preferred ports are busy, otherwise an exception will be raised.
            range: The range of ports to search for a free port.

        Returns:
            An available TCP port number

        Raises:
            IOError: if the preferred TCP port is busy and
                `allocate_port_if_busy` is disabled, or if no free TCP port
                could be otherwise allocated.
        """
        # If a port value is explicitly configured, attempt to use it first
        if preferred_ports:
            for port in preferred_ports:
                if port_available(port):
                    return port
            if not allocate_port_if_busy:
                raise IOError(f"TCP port {preferred_ports} is not available.")

        port = scan_for_available_port(start=range[0], stop=range[1])
        if port:
            return port
        raise IOError(f"No free TCP ports found in range {range}")

    def _get_container_id(self, endpoint: PipelineEndpointResponse) -> str:
        """Get the docker container id associated with a pipeline endpoint.

        Args:
            endpoint: The pipeline endpoint to get the container id for.

        Returns:
            The docker container id for the pipeline endpoint.
        """
        return f"zenml-pipeline-endpoint-{endpoint.id}"

    def _get_container(
        self, endpoint: PipelineEndpointResponse
    ) -> Optional[Container]:
        """Get the docker container associated with a pipeline endpoint.

        Returns:
            The docker container for the service, or None if the container
            does not exist.
        """
        metadata = DockerPipelineEndpointMetadata.from_endpoint(endpoint)
        if metadata.container_id is None:
            return None
        try:
            return self.docker_client.containers.get(metadata.container_id)
        except docker_errors.NotFound:
            # container doesn't exist yet or was removed
            return None

    def _get_container_image(
        self, deployment: PipelineDeploymentResponse
    ) -> str:
        """Get the docker image used to serve a pipeline deployment.

        Args:
            deployment: The pipeline deployment to get the image for.

        Returns:
            The docker image used to serve the pipeline deployment.
        """
        if deployment.build is None:
            raise ValueError(
                "Pipeline deployment does not have a build. "
                "Please run a build before serving the pipeline."
            )
        if len(deployment.build.images) == 0:
            raise ValueError(
                "Pipeline deployment build does not have any images. "
                "Please run a containerized build before serving the pipeline."
            )
        return list(deployment.build.images.values())[0].image

    def _get_container_operational_state(
        self, container: Container
    ) -> PipelineEndpointOperationalState:
        """Get the operational state of a docker container serving a pipeline endpoint.

        Args:
            container: The docker container to get the operational state of.

        Returns:
            The operational state of the docker container serving the pipeline
            endpoint.
        """
        metadata = DockerPipelineEndpointMetadata.from_container(container)
        state = PipelineEndpointOperationalState(
            status=PipelineEndpointStatus.UNKNOWN,
            metadata=metadata.model_dump(exclude_none=True),
        )
        if metadata.container_status == "running":
            state.status = PipelineEndpointStatus.RUNNING
        elif metadata.container_status == "exited":
            state.status = PipelineEndpointStatus.ERROR
        elif metadata.container_status in ["created", "restarting", "paused"]:
            state.status = PipelineEndpointStatus.DEPLOYING
        elif metadata.container_status == "dead":
            state.status = PipelineEndpointStatus.ERROR
        elif metadata.container_status == "removing":
            state.status = PipelineEndpointStatus.DELETING
        elif metadata.container_status == "exited":
            state.status = PipelineEndpointStatus.DELETED
        elif metadata.container_status == "dead":
            state.status = PipelineEndpointStatus.ERROR

        if state.status == PipelineEndpointStatus.RUNNING:
            state.url = f"http://localhost:{metadata.port}"
            # TODO: check if the endpoint is healthy.

        return state

    def do_serve_pipeline(
        self,
        endpoint: PipelineEndpointResponse,
        stack: "Stack",
        environment: Optional[Dict[str, str]] = None,
        secrets: Optional[Dict[str, str]] = None,
    ) -> PipelineEndpointOperationalState:
        """Serve a pipeline as a Docker container.

        Args:
            endpoint: The pipeline endpoint to serve as a Docker container.
            stack: The stack the pipeline will be served on.
            environment: A dictionary of environment variables to set on the
                pipeline endpoint.
            secrets: A dictionary of secret environment variables to set
                on the pipeline endpoint. These secret environment variables
                should not be exposed as regular environment variables on the
                pipeline server.

        Returns:
            The PipelineEndpointOperationalState object representing the
            operational state of the deployed pipeline endpoint.

        Raises:
            PipelineEndpointDeploymentError: if the pipeline endpoint deployment
                fails.
            PipelineServerError: if an unexpected error occurs.
        """
        deployment = endpoint.pipeline_deployment
        assert deployment, "Pipeline deployment not found"

        environment = environment or {}
        secrets = secrets or {}
        # Currently, there is no safe way to pass secrets to a docker
        # container, so we simply merge them into the environment variables.
        environment.update(secrets)

        settings = cast(
            DockerPipelineServerSettings,
            self.get_settings(deployment),
        )

        existing_metadata = DockerPipelineEndpointMetadata.from_endpoint(
            endpoint
        )

        entrypoint = ServingPipelineEntrypoint.get_entrypoint_command()

        arguments = ServingPipelineEntrypoint.get_entrypoint_arguments(
            deployment_id=deployment.id,
            runtime_params={},
            create_zen_run=False,
        )

        # Add the local stores path as a volume mount
        stack.check_local_paths()
        local_stores_path = GlobalConfiguration().local_stores_path
        volumes = {
            local_stores_path: {
                "bind": local_stores_path,
                "mode": "rw",
            }
        }
        environment[ENV_ZENML_LOCAL_STORES_PATH] = local_stores_path

        # check if a container already exists for the endpoint
        container = self._get_container(endpoint)

        if container:
            # the container exists, check if it is running
            if container.status == "running":
                logger.debug(
                    f"Container for pipeline endpoint '{endpoint.name}' is "
                    "already running",
                )
                container.stop()

            # the container is stopped or in an error state, remove it
            logger.debug(
                f"Removing previous container for pipeline endpoint "
                f"'{endpoint.name}'",
            )
            container.remove(force=True)

        logger.debug(
            f"Starting container for pipeline endpoint '{endpoint.name}'..."
        )

        assert endpoint.pipeline_deployment, "Pipeline deployment not found"
        image = self._get_container_image(endpoint.pipeline_deployment)

        try:
            self.docker_client.images.get(image)
        except docker_errors.ImageNotFound:
            logger.debug(
                f"Pulling container image '{image}' for pipeline endpoint "
                f"'{endpoint.name}'...",
            )
            self.docker_client.images.pull(image)

        ports: Dict[str, Optional[int]] = {}
        preferred_ports: List[int] = []
        if settings.port:
            preferred_ports.append(settings.port)
        if existing_metadata.port:
            preferred_ports.append(existing_metadata.port)
        port = self._lookup_free_port(
            preferred_ports=preferred_ports,
            allocate_port_if_busy=settings.allocate_port_if_busy,
            range=settings.port_range,
        )
        ports[f"{port}/tcp"] = port

        uid_args: Dict[str, Any] = {}
        if sys.platform == "win32":
            # File permissions are not checked on Windows. This if clause
            # prevents mypy from complaining about unused 'type: ignore'
            # statements
            pass
        else:
            # Run the container in the context of the local UID/GID
            # to ensure that the local database can be shared
            # with the container.
            logger.debug(
                "Setting UID and GID to local user/group in container."
            )
            uid_args = dict(
                user=os.getuid(),
                group_add=[os.getgid()],
            )

        run_args = copy.deepcopy(settings.run_args)
        docker_environment = run_args.pop("environment", {})
        docker_environment.update(environment)

        docker_volumes = run_args.pop("volumes", {})
        docker_volumes.update(volumes)

        extra_hosts = run_args.pop("extra_hosts", {})
        extra_hosts["host.docker.internal"] = "host-gateway"

        run_args.update(uid_args)

        try:
            self.docker_client.containers.run(
                image=image,
                name=self._get_container_id(endpoint),
                entrypoint=entrypoint,
                command=arguments,
                detach=True,
                volumes=docker_volumes,
                environment=docker_environment,
                remove=True,
                auto_remove=True,
                ports=ports,
                labels={
                    "zenml-pipeline-endpoint-uuid": str(endpoint.id),
                    "zenml-pipeline-endpoint-name": endpoint.name,
                },
                extra_hosts=extra_hosts,
                **run_args,
            )

            logger.debug(
                f"Docker container for pipeline endpoint '{endpoint.name}' "
                f"started with ID {self._get_container_id(endpoint)}",
            )
        except docker_errors.DockerException as e:
            raise PipelineEndpointDeploymentError(
                f"Docker container for pipeline endpoint '{endpoint.name}' "
                f"failed to start: {e}"
            )

        return self.do_get_pipeline_endpoint(endpoint)

    def do_get_pipeline_endpoint(
        self,
        endpoint: PipelineEndpointResponse,
    ) -> PipelineEndpointOperationalState:
        """Get information about a docker pipeline endpoint.

        Args:
            endpoint: The pipeline endpoint to get information about.

        Returns:
            The PipelineEndpointOperationalState object representing the
            updated operational state of the pipeline endpoint.

        Raises:
            PipelineEndpointNotFoundError: if no pipeline endpoint is found
                corresponding to the provided PipelineEndpointResponse.
            PipelineServerError: if the pipeline endpoint information cannot
                be retrieved for any other reason or if an unexpected error
                occurs.
        """
        container = self._get_container(endpoint)
        if container is None:
            raise PipelineEndpointNotFoundError(
                f"Docker container for pipeline endpoint '{endpoint.name}' "
                "not found"
            )

        return self._get_container_operational_state(container)

    def do_get_pipeline_endpoint_logs(
        self,
        endpoint: PipelineEndpointResponse,
        follow: bool = False,
        tail: Optional[int] = None,
    ) -> Generator[str, bool, None]:
        """Abstract method to get the logs of a pipeline endpoint.

        Args:
            endpoint: The pipeline endpoint to get the logs of.
            follow: if True, the logs will be streamed as they are written
            tail: only retrieve the last NUM lines of log output.

        Returns:
            A generator that yields the logs of the pipeline endpoint.

        Raises:
            PipelineEndpointNotFoundError: if no pipeline endpoint is found
                corresponding to the provided PipelineEndpointResponse.
            PipelineLogsNotFoundError: if the pipeline endpoint logs are not
                found.
            PipelineServerError: if the pipeline endpoint logs cannot
                be retrieved for any other reason or if an unexpected error
                occurs.
        """
        yield ""

    def do_delete_pipeline_endpoint(
        self,
        endpoint: PipelineEndpointResponse,
    ) -> Optional[PipelineEndpointOperationalState]:
        """Delete a docker pipeline endpoint.

        Args:
            endpoint: The pipeline endpoint to delete.

        Returns:
            The PipelineEndpointOperationalState object representing the
            operational state of the deleted pipeline endpoint, or None if the
            deletion is completed before the call returns.

        Raises:
            PipelineEndpointNotFoundError: if no pipeline endpoint is found
                corresponding to the provided PipelineEndpointResponse.
            PipelineEndpointDeletionError: if the pipeline endpoint deletion
                fails.
        """
        container = self._get_container(endpoint)
        if container is None:
            raise PipelineEndpointNotFoundError(
                f"Docker container for pipeline endpoint '{endpoint.name}' "
                "not found"
            )

        try:
            container.stop()
            container.remove()
        except docker_errors.DockerException as e:
            raise PipelineEndpointDeletionError(
                f"Docker container for pipeline endpoint '{endpoint.name}' "
                f"failed to delete: {e}"
            )

        state = self._get_container_operational_state(container)
        # Report a DELETING state to indicate that the deletion is in progress
        # and force the base class
        state.status = PipelineEndpointStatus.DELETING
        return state


class DockerPipelineServerSettings(BaseSettings):
    """Local Docker pipeline server settings.

    Attributes:
        port: The port to serve the pipeline endpoint on.
        allocate_port_if_busy: If True, allocate a free port if the configured
            port is busy.
        port_range: The range of ports to search for a free port.
        run_args: Arguments to pass to the `docker run` call. (See
            https://docker-py.readthedocs.io/en/stable/containers.html for a list
            of what can be passed.)
    """

    port: Optional[int] = None
    allocate_port_if_busy: bool = True
    port_range: Tuple[int, int] = (8000, 65535)
    run_args: Dict[str, Any] = {}


class DockerPipelineServerConfig(
    BasePipelineServerConfig, DockerPipelineServerSettings
):
    """Local Docker pipeline server config."""

    @property
    def is_local(self) -> bool:
        """Checks if this stack component is running locally.

        Returns:
            True if this config is for a local component, False otherwise.
        """
        return True


class DockerPipelineServerFlavor(BasePipelineServerFlavor):
    """Flavor for the local Docker pipeline server."""

    @property
    def name(self) -> str:
        """Name of the orchestrator flavor.

        Returns:
            Name of the orchestrator flavor.
        """
        return "docker"

    @property
    def docs_url(self) -> Optional[str]:
        """A url to point at docs explaining this flavor.

        Returns:
            A flavor docs url.
        """
        return self.generate_default_docs_url()

    @property
    def sdk_docs_url(self) -> Optional[str]:
        """A url to point at SDK docs explaining this flavor.

        Returns:
            A flavor SDK docs url.
        """
        return self.generate_default_sdk_docs_url()

    @property
    def logo_url(self) -> str:
        """A url to represent the flavor in the dashboard.

        Returns:
            The flavor logo.
        """
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/orchestrator/docker.png"

    @property
    def config_class(self) -> Type[BasePipelineServerConfig]:
        """Config class for the base orchestrator flavor.

        Returns:
            The config class.
        """
        return DockerPipelineServerConfig

    @property
    def implementation_class(self) -> Type["DockerPipelineServer"]:
        """Implementation class for this flavor.

        Returns:
            Implementation class for this flavor.
        """
        return DockerPipelineServer
