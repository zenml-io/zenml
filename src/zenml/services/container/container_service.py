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
"""Implementation of a containerized ZenML service."""

import os
import pathlib
import sys
import tempfile
import time
from abc import abstractmethod
from typing import Any, Dict, Generator, List, Optional, Tuple

import docker.errors as docker_errors
from docker.client import DockerClient
from docker.models.containers import Container
from pydantic import Field

from zenml.constants import ENV_ZENML_CONFIG_PATH
from zenml.logger import get_logger
from zenml.services.container.container_service_endpoint import (
    ContainerServiceEndpoint,
)
from zenml.services.service import BaseService, ServiceConfig
from zenml.services.service_status import ServiceState, ServiceStatus
from zenml.utils import docker_utils
from zenml.utils.io_utils import (
    create_dir_recursive_if_not_exists,
    get_global_config_directory,
)

logger = get_logger(__name__)


SERVICE_CONTAINER_PATH = "/service"
SERVICE_LOG_FILE_NAME = "service.log"
SERVICE_CONFIG_FILE_NAME = "service.json"
SERVICE_CONTAINER_GLOBAL_CONFIG_DIR = "zenconfig"
SERVICE_CONTAINER_GLOBAL_CONFIG_PATH = os.path.join(
    "/", SERVICE_CONTAINER_GLOBAL_CONFIG_DIR
)
DOCKER_ZENML_SERVER_DEFAULT_IMAGE = "zenmldocker/zenml"
ENV_ZENML_SERVICE_CONTAINER = "ZENML_SERVICE_CONTAINER"


class ContainerServiceConfig(ServiceConfig):
    """containerized service configuration.

    Attributes:
        root_runtime_path: the root path where the service stores its files.
        singleton: set to True to store the service files directly in the
            `root_runtime_path` directory instead of creating a subdirectory for
            each service instance. Only has effect if the `root_runtime_path` is
            also set.
        image: the container image to use for the service.
    """

    root_runtime_path: Optional[str] = None
    singleton: bool = False
    image: str = DOCKER_ZENML_SERVER_DEFAULT_IMAGE


class ContainerServiceStatus(ServiceStatus):
    """containerized service status.

    Attributes:
        runtime_path: the path where the service files (e.g. the configuration
            file used to start the service daemon and the logfile) are located
    """

    runtime_path: Optional[str] = None

    @property
    def config_file(self) -> Optional[str]:
        """Get the path to the service configuration file.

        Returns:
            The path to the configuration file, or None, if the
            service has never been started before.
        """
        if not self.runtime_path:
            return None
        return os.path.join(self.runtime_path, SERVICE_CONFIG_FILE_NAME)

    @property
    def log_file(self) -> Optional[str]:
        """Get the path to the log file where the service output is/has been logged.

        Returns:
            The path to the log file, or None, if the service has never been
            started before.
        """
        if not self.runtime_path:
            return None
        return os.path.join(self.runtime_path, SERVICE_LOG_FILE_NAME)


class ContainerService(BaseService):
    """A service represented by a containerized process.

    This class extends the base service class with functionality concerning
    the life-cycle management and tracking of external services implemented as
    docker containers.

    To define a containerized service, subclass this class and implement the
    `run` method. Upon `start`, the service will spawn a container that
    ends up calling the `run` method.

    For example,

    ```python

    from zenml.services import ServiceType, ContainerService, ContainerServiceConfig
    import time

    class SleepingServiceConfig(ContainerServiceConfig):

        wake_up_after: int

    class SleepingService(ContainerService):

        SERVICE_TYPE = ServiceType(
            name="sleeper",
            description="Sleeping container",
            type="container",
            flavor="sleeping",
        )
        config: SleepingServiceConfig

        def run(self) -> None:
            time.sleep(self.config.wake_up_after)

    service = SleepingService(config=SleepingServiceConfig(wake_up_after=10))
    service.start()
    ```

    NOTE: the `SleepingService` class and its parent module have to be
    discoverable as part of a ZenML `Integration`, otherwise the daemon will
    fail with the following error:

    ```
    TypeError: Cannot load service with unregistered service type:
    name='sleeper' type='container' flavor='sleeping' description='Sleeping container'
    ```

    Attributes:
        config: service configuration
        status: service status
        endpoint: optional service endpoint
    """

    config: ContainerServiceConfig = Field(
        default_factory=ContainerServiceConfig
    )
    status: ContainerServiceStatus = Field(
        default_factory=ContainerServiceStatus
    )
    # TODO [ENG-705]: allow multiple endpoints per service
    endpoint: Optional[ContainerServiceEndpoint] = None

    _docker_client: Optional[DockerClient] = None

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

    @property
    def container_id(self) -> str:
        """Get the ID of the docker container for a service.

        Returns:
            The ID of the docker container for the service.
        """
        return f"zenml-{str(self.uuid)}"

    def get_service_status_message(self) -> str:
        """Get a message about the current operational state of the service.

        Returns:
            A message providing information about the current operational
            state of the service.
        """
        msg = super().get_service_status_message()
        msg += f"  Container ID: `{self.container_id}`\n"
        if self.status.log_file:
            msg += (
                f"For more information on the service status, please see the "
                f"following log file: {self.status.log_file}\n"
            )
        return msg

    def check_status(self) -> Tuple[ServiceState, str]:
        """Check the the current operational state of the docker container.

        Returns:
            The operational state of the docker container and a message
            providing additional information about that state (e.g. a
            description of the error, if one is encountered).
        """
        container: Optional[Container] = None
        try:
            container = self.docker_client.containers.get(self.container_id)
        except docker_errors.NotFound:
            # container doesn't exist yet or was removed
            pass

        if container is None:
            return ServiceState.INACTIVE, "Docker container is not present"
        elif container.status == "running":
            return ServiceState.ACTIVE, "Docker container is running"
        elif container.status == "exited":
            return (
                ServiceState.ERROR,
                "Docker container has exited.",
            )
        else:
            return (
                ServiceState.INACTIVE,
                f"Docker container is {container.status}",
            )

    def _setup_runtime_path(self) -> None:
        """Set up the runtime path for the service.

        This method sets up the runtime path for the service.
        """
        # reuse the config file and logfile location from a previous run,
        # if available
        if not self.status.runtime_path or not os.path.exists(
            self.status.runtime_path
        ):
            if self.config.root_runtime_path:
                if self.config.singleton:
                    self.status.runtime_path = self.config.root_runtime_path
                else:
                    self.status.runtime_path = os.path.join(
                        self.config.root_runtime_path,
                        str(self.uuid),
                    )
                create_dir_recursive_if_not_exists(self.status.runtime_path)
            else:
                self.status.runtime_path = tempfile.mkdtemp(
                    prefix="zenml-service-"
                )

    def _get_container_cmd(self) -> Tuple[List[str], Dict[str, str]]:
        """Get the command to run the service container.

        The default implementation provided by this class is the following:

          * this ContainerService instance and its configuration
          are serialized as JSON and saved to a file
          * the entrypoint.py script is launched as a docker container
          and pointed to the serialized service file
          * the entrypoint script re-creates the ContainerService instance
          from the serialized configuration, then calls the `run`
          method that must be implemented by the subclass

        Subclasses that need a different command to launch the container
        should override this method.

        Returns:
            Command needed to launch the docker container and the environment
            variables to set, in the formats accepted by subprocess.Popen.
        """
        # to avoid circular imports, import here
        from zenml.services.container import entrypoint

        assert self.status.config_file is not None
        assert self.status.log_file is not None

        with open(self.status.config_file, "w") as f:
            f.write(self.model_dump_json(indent=4))
        pathlib.Path(self.status.log_file).touch()

        command = [
            "python",
            "-m",
            entrypoint.__name__,
            "--config-file",
            os.path.join(SERVICE_CONTAINER_PATH, SERVICE_CONFIG_FILE_NAME),
        ]

        command_env = {
            ENV_ZENML_SERVICE_CONTAINER: "true",
        }
        for k, v in os.environ.items():
            if k.startswith("ZENML_"):
                command_env[k] = v
        # the global configuration is mounted into the container at a
        # different location
        command_env[ENV_ZENML_CONFIG_PATH] = (
            SERVICE_CONTAINER_GLOBAL_CONFIG_PATH
        )

        return command, command_env

    def _get_container_volumes(self) -> Dict[str, Dict[str, str]]:
        """Get the volumes to mount into the service container.

        The default implementation provided by this class mounts the
        following directories into the container:

          * the service runtime path
          * the global configuration directory

        Subclasses that need to mount additional volumes should override
        this method.

        Returns:
            A dictionary mapping host paths to dictionaries containing
            the mount options for each volume.
        """
        volumes: Dict[str, Dict[str, str]] = {}

        assert self.status.runtime_path is not None

        volumes[self.status.runtime_path] = {
            "bind": SERVICE_CONTAINER_PATH,
            "mode": "rw",
        }

        volumes[get_global_config_directory()] = {
            "bind": SERVICE_CONTAINER_GLOBAL_CONFIG_PATH,
            "mode": "rw",
        }

        return volumes

    @property
    def container(self) -> Optional[Container]:
        """Get the docker container for the service.

        Returns:
            The docker container for the service, or None if the container
            does not exist.
        """
        try:
            return self.docker_client.containers.get(self.container_id)
        except docker_errors.NotFound:
            # container doesn't exist yet or was removed
            return None

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
                    "Setting UID and GID to local user/group " "in container."
                )
                uid_args = dict(
                    user=os.getuid(),
                    group_add=[os.getgid()],
                )

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
                labels={
                    "zenml-service-uuid": str(self.uuid),
                },
                working_dir=SERVICE_CONTAINER_PATH,
                extra_hosts={"host.docker.internal": "host-gateway"},
                **uid_args,
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

    def _stop_daemon(self, force: bool = False) -> None:
        """Stop the service docker container associated with this service.

        Args:
            force: if True, the service container will be forcefully stopped
        """
        container = self.container
        if not container:
            # service container is not running
            logger.debug(
                "Docker container for service '%s' no longer running",
                self,
            )
            return

        logger.debug("Stopping container for service '%s' ...", self)
        if force:
            container.kill()
            container.remove(force=True)
        else:
            container.stop()
            container.remove()

    def provision(self) -> None:
        """Provision the service."""
        self._start_container()

    def deprovision(self, force: bool = False) -> None:
        """Deprovision the service.

        Args:
            force: if True, the service container will be forcefully stopped
        """
        self._stop_daemon(force)

    def get_logs(
        self, follow: bool = False, tail: Optional[int] = None
    ) -> Generator[str, bool, None]:
        """Retrieve the service logs.

        Args:
            follow: if True, the logs will be streamed as they are written
            tail: only retrieve the last NUM lines of log output.
        """
        if not self.status.log_file or not os.path.exists(
            self.status.log_file
        ):
            return

        with open(self.status.log_file, "r") as f:
            if tail:
                # TODO[ENG-864]: implement a more efficient tailing mechanism that
                #   doesn't read the entire file
                lines = f.readlines()[-tail:]
                for line in lines:
                    yield line.rstrip("\n")
                if not follow:
                    return
            line = ""
            while True:
                partial_line = f.readline()
                if partial_line:
                    line += partial_line
                    if line.endswith("\n"):
                        stop = yield line.rstrip("\n")
                        if stop:
                            break
                        line = ""
                elif follow:
                    time.sleep(1)
                else:
                    break

    @abstractmethod
    def run(self) -> None:
        """Run the containerized service logic associated with this service.

        Subclasses must implement this method to provide the containerized
        service functionality. This method will be executed in the context of
        the running container, not in the context of the process that calls the
        `start` method.
        """
