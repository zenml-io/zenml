#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""Implementation of the ZenML Docker deployer."""

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
from zenml.deployers.base_deployer import (
    BaseDeployerConfig,
    BaseDeployerFlavor,
    BaseDeployerSettings,
)
from zenml.deployers.containerized_deployer import (
    ContainerizedDeployer,
)
from zenml.deployers.exceptions import (
    DeployerError,
    DeploymentDeprovisionError,
    DeploymentLogsNotFoundError,
    DeploymentNotFoundError,
    DeploymentProvisionError,
)
from zenml.deployers.server.entrypoint_configuration import (
    DEPLOYMENT_ID_OPTION,
    DeploymentEntrypointConfiguration,
)
from zenml.enums import DeploymentStatus, StackComponentType
from zenml.logger import get_logger
from zenml.models import (
    DeploymentOperationalState,
    DeploymentResponse,
)
from zenml.stack import Stack, StackValidator
from zenml.utils import docker_utils
from zenml.utils.networking_utils import (
    lookup_preferred_or_free_port,
)

logger = get_logger(__name__)


class DockerDeploymentMetadata(BaseModel):
    """Metadata for a Docker deployment."""

    port: Optional[int] = None
    container_id: Optional[str] = None
    container_name: Optional[str] = None
    container_image_id: Optional[str] = None
    container_image_uri: Optional[str] = None
    container_status: Optional[str] = None

    @classmethod
    def from_container(
        cls, container: Container
    ) -> "DockerDeploymentMetadata":
        """Create a DockerDeploymentMetadata from a docker container.

        Args:
            container: The docker container to get the metadata for.

        Returns:
            The metadata for the docker container.
        """
        image = container.image
        if image is not None:
            image_url = image.attrs["RepoTags"][0]
            image_id = image.attrs["Id"]
        else:
            image_url = None
            image_id = None
        if container.ports:
            ports = list(container.ports.values())
            if len(ports) > 0:
                port = int(ports[0][0]["HostPort"])
            else:
                port = None
        else:
            port = None
        return cls(
            port=port,
            container_id=container.id,
            container_name=container.name,
            container_image_uri=image_url,
            container_image_id=image_id,
            container_status=container.status,
        )

    @classmethod
    def from_deployment(
        cls, deployment: DeploymentResponse
    ) -> "DockerDeploymentMetadata":
        """Create a DockerDeploymentMetadata from a deployment.

        Args:
            deployment: The deployment to get the metadata for.

        Returns:
            The metadata for the deployment.
        """
        return cls.model_validate(deployment.deployment_metadata)


class DockerDeployer(ContainerizedDeployer):
    """Deployer responsible for deploying pipelines locally using Docker."""

    _docker_client: Optional[DockerClient] = None

    @property
    def settings_class(self) -> Optional[Type["BaseSettings"]]:
        """Settings class for the Docker deployer.

        Returns:
            The settings class.
        """
        return DockerDeployerSettings

    @property
    def config(self) -> "DockerDeployerConfig":
        """Returns the `DockerDeployerConfig` config.

        Returns:
            The configuration.
        """
        return cast(DockerDeployerConfig, self._config)

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

    def _get_container_id(self, deployment: DeploymentResponse) -> str:
        """Get the docker container id associated with a deployment.

        Args:
            deployment: The deployment to get the container id for.

        Returns:
            The docker container id for the deployment.
        """
        return f"zenml-deployment-{deployment.id}"

    def _get_container(
        self, deployment: DeploymentResponse
    ) -> Optional[Container]:
        """Get the docker container associated with a deployment.

        Args:
            deployment: The deployment to get the container for.

        Returns:
            The docker container for the service, or None if the container
            does not exist.
        """
        try:
            return self.docker_client.containers.get(
                self._get_container_id(deployment)
            )
        except docker_errors.NotFound:
            # container doesn't exist yet or was removed
            return None

    def _get_container_operational_state(
        self, container: Container
    ) -> DeploymentOperationalState:
        """Get the operational state of a docker container running a deployment.

        Args:
            container: The docker container to get the operational state of.

        Returns:
            The operational state of the docker container running the pipeline
            deployment.
        """
        metadata = DockerDeploymentMetadata.from_container(container)
        state = DeploymentOperationalState(
            status=DeploymentStatus.UNKNOWN,
            metadata=metadata.model_dump(exclude_none=True),
        )
        if metadata.container_status == "running":
            state.status = DeploymentStatus.RUNNING
        elif metadata.container_status == "exited":
            state.status = DeploymentStatus.ERROR
        elif metadata.container_status in ["created", "restarting", "paused"]:
            state.status = DeploymentStatus.PENDING
        elif metadata.container_status == "dead":
            state.status = DeploymentStatus.ERROR
        elif metadata.container_status == "removing":
            state.status = DeploymentStatus.PENDING
        elif metadata.container_status == "exited":
            state.status = DeploymentStatus.ABSENT
        elif metadata.container_status == "dead":
            state.status = DeploymentStatus.ERROR

        if state.status == DeploymentStatus.RUNNING:
            state.url = "http://localhost"
            if metadata.port:
                state.url += f":{metadata.port}"

        return state

    def do_provision_deployment(
        self,
        deployment: DeploymentResponse,
        stack: "Stack",
        environment: Dict[str, str],
        secrets: Dict[str, str],
        timeout: int,
    ) -> DeploymentOperationalState:
        """Deploy a pipeline as a Docker container.

        Args:
            deployment: The deployment to run as a Docker container.
            stack: The stack the pipeline will be deployed on.
            environment: A dictionary of environment variables to set on the
                deployment.
            secrets: A dictionary of secret environment variables to set
                on the deployment. These secret environment variables
                should not be exposed as regular environment variables on the
                deployer.
            timeout: The maximum time in seconds to wait for the pipeline
                deployment to be provisioned.

        Returns:
            The DeploymentOperationalState object representing the
            operational state of the provisioned deployment.

        Raises:
            DeploymentProvisionError: if provisioning the deployment
                fails.
        """
        assert deployment.snapshot, "Pipeline snapshot not found"
        snapshot = deployment.snapshot

        # Currently, there is no safe way to pass secrets to a docker
        # container, so we simply merge them into the environment variables.
        environment.update(secrets)

        settings = cast(
            DockerDeployerSettings,
            self.get_settings(snapshot),
        )

        existing_metadata = DockerDeploymentMetadata.from_deployment(
            deployment
        )

        entrypoint = DeploymentEntrypointConfiguration.get_entrypoint_command()

        entrypoint_kwargs = {
            DEPLOYMENT_ID_OPTION: deployment.id,
        }

        arguments = DeploymentEntrypointConfiguration.get_entrypoint_arguments(
            **entrypoint_kwargs
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

        # check if a container already exists for the deployment
        container = self._get_container(deployment)

        if container:
            # the container exists, check if it is running
            if container.status == "running":
                logger.debug(
                    f"Container for deployment '{deployment.name}' is "
                    "already running",
                )
                container.stop(timeout=timeout)

            # the container is stopped or in an error state, remove it
            logger.debug(
                f"Removing previous container for deployment "
                f"'{deployment.name}'",
            )
            container.remove(force=True)

        logger.debug(
            f"Starting container for deployment '{deployment.name}'..."
        )

        image = self.get_image(deployment.snapshot)

        try:
            self.docker_client.images.get(image)
        except docker_errors.ImageNotFound:
            logger.debug(
                f"Pulling container image '{image}' for deployment "
                f"'{deployment.name}'...",
            )
            self.docker_client.images.pull(image)

        preferred_ports: List[int] = []
        if settings.port:
            preferred_ports.append(settings.port)
        if existing_metadata.port:
            preferred_ports.append(existing_metadata.port)
        port = lookup_preferred_or_free_port(
            preferred_ports=preferred_ports,
            allocate_port_if_busy=settings.allocate_port_if_busy,
            range=settings.port_range,
            address="0.0.0.0",  # nosec
        )
        container_port = (
            snapshot.pipeline_configuration.deployment_settings.uvicorn_port
        )
        ports: Dict[str, Optional[int]] = {f"{container_port}/tcp": port}

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
            container = self.docker_client.containers.run(
                image=image,
                name=self._get_container_id(deployment),
                entrypoint=entrypoint,
                command=arguments,
                detach=True,
                volumes=docker_volumes,
                environment=docker_environment,
                remove=False,
                auto_remove=False,
                ports=ports,
                labels={
                    "zenml-deployment-id": str(deployment.id),
                    "zenml-deployment-name": deployment.name,
                    "zenml-deployer-name": str(self.name),
                    "zenml-deployer-id": str(self.id),
                    "managed-by": "zenml",
                },
                extra_hosts=extra_hosts,
                **run_args,
            )

            logger.debug(
                f"Docker container for deployment '{deployment.name}' "
                f"started with ID {self._get_container_id(deployment)}",
            )

        except docker_errors.DockerException as e:
            raise DeploymentProvisionError(
                f"Docker container for deployment '{deployment.name}' "
                f"failed to start: {e}"
            )

        return self._get_container_operational_state(container)

    def do_get_deployment_state(
        self,
        deployment: DeploymentResponse,
    ) -> DeploymentOperationalState:
        """Get information about a docker deployment.

        Args:
            deployment: The deployment to get information about.

        Returns:
            The DeploymentOperationalState object representing the
            updated operational state of the deployment.

        Raises:
            DeploymentNotFoundError: if no deployment is found
                corresponding to the provided DeploymentResponse.
        """
        container = self._get_container(deployment)
        if container is None:
            raise DeploymentNotFoundError(
                f"Docker container for deployment '{deployment.name}' "
                "not found"
            )

        return self._get_container_operational_state(container)

    def do_get_deployment_state_logs(
        self,
        deployment: DeploymentResponse,
        follow: bool = False,
        tail: Optional[int] = None,
    ) -> Generator[str, bool, None]:
        """Get the logs of a Docker deployment.

        Args:
            deployment: The deployment to get the logs of.
            follow: if True, the logs will be streamed as they are written
            tail: only retrieve the last NUM lines of log output.

        Yields:
            The logs of the deployment.

        Raises:
            DeploymentNotFoundError: if no deployment is found
                corresponding to the provided DeploymentResponse.
            DeploymentLogsNotFoundError: if the deployment logs are not
                found.
            DeployerError: if the deployment logs cannot
                be retrieved for any other reason or if an unexpected error
                occurs.
        """
        container = self._get_container(deployment)
        if container is None:
            raise DeploymentNotFoundError(
                f"Docker container for deployment '{deployment.name}' "
                "not found"
            )

        try:
            log_kwargs: Dict[str, Any] = {
                "stdout": True,
                "stderr": True,
                "stream": follow,
                "follow": follow,
                "timestamps": True,
            }

            if tail is not None and tail > 0:
                log_kwargs["tail"] = tail

            log_stream = container.logs(**log_kwargs)

            if follow:
                for log_line in log_stream:
                    if isinstance(log_line, bytes):
                        yield log_line.decode(
                            "utf-8", errors="replace"
                        ).rstrip()
                    else:
                        yield str(log_line).rstrip()
            else:
                if isinstance(log_stream, bytes):
                    log_text = log_stream.decode("utf-8", errors="replace")
                    for line in log_text.splitlines():
                        yield line
                else:
                    for log_line in log_stream:
                        if isinstance(log_line, bytes):
                            yield log_line.decode(
                                "utf-8", errors="replace"
                            ).rstrip()
                        else:
                            yield str(log_line).rstrip()

        except docker_errors.NotFound as e:
            raise DeploymentLogsNotFoundError(
                f"Logs for deployment '{deployment.name}' not found: {e}"
            )
        except docker_errors.APIError as e:
            raise DeployerError(
                f"Docker API error while retrieving logs for deployment "
                f"'{deployment.name}': {e}"
            )
        except docker_errors.DockerException as e:
            raise DeployerError(
                f"Docker error while retrieving logs for deployment "
                f"'{deployment.name}': {e}"
            )
        except Exception as e:
            raise DeployerError(
                f"Unexpected error while retrieving logs for deployment "
                f"'{deployment.name}': {e}"
            )

    def do_deprovision_deployment(
        self,
        deployment: DeploymentResponse,
        timeout: int,
    ) -> Optional[DeploymentOperationalState]:
        """Deprovision a docker deployment.

        Args:
            deployment: The deployment to deprovision.
            timeout: The maximum time in seconds to wait for the pipeline
                deployment to be deprovisioned.

        Returns:
            The DeploymentOperationalState object representing the
            operational state of the deleted deployment, or None if the
            deletion is completed before the call returns.

        Raises:
            DeploymentNotFoundError: if no deployment is found
                corresponding to the provided DeploymentResponse.
            DeploymentDeprovisionError: if the deployment
                deprovision fails.
        """
        container = self._get_container(deployment)
        if container is None:
            raise DeploymentNotFoundError(
                f"Docker container for deployment '{deployment.name}' "
                "not found"
            )

        try:
            container.stop(timeout=timeout)
            container.remove()
        except docker_errors.DockerException as e:
            raise DeploymentDeprovisionError(
                f"Docker container for deployment '{deployment.name}' "
                f"failed to delete: {e}"
            )

        return None


class DockerDeployerSettings(BaseDeployerSettings):
    """Docker deployer settings.

    Attributes:
        port: The port to expose the deployment on.
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


class DockerDeployerConfig(BaseDeployerConfig, DockerDeployerSettings):
    """Docker deployer config."""

    @property
    def is_local(self) -> bool:
        """Checks if this stack component is running locally.

        Returns:
            True if this config is for a local component, False otherwise.
        """
        return True


class DockerDeployerFlavor(BaseDeployerFlavor):
    """Flavor for the Docker deployer."""

    @property
    def name(self) -> str:
        """Name of the deployer flavor.

        Returns:
            Name of the deployer flavor.
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
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/deployer/docker.png"

    @property
    def config_class(self) -> Type[BaseDeployerConfig]:
        """Config class for the base deployer flavor.

        Returns:
            The config class.
        """
        return DockerDeployerConfig

    @property
    def implementation_class(self) -> Type["DockerDeployer"]:
        """Implementation class for this flavor.

        Returns:
            Implementation class for this flavor.
        """
        return DockerDeployer
