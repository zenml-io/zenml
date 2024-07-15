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
"""Docker-compose ZenML server deployment."""

import logging
import time
from typing import Optional

import docker.errors as docker_errors
from docker.models.containers import Container

from tests.harness.deployment.base import (
    DEPLOYMENT_START_TIMEOUT,
    LOCAL_ZENML_SERVER_DEFAULT_PORT,
    MARIADB_DEFAULT_PORT,
    MARIADB_DOCKER_IMAGE,
    MARIADB_ROOT_PASSWORD,
    ZENML_SERVER_IMAGE_NAME,
    BaseTestDeployment,
)
from tests.harness.model import (
    DatabaseType,
    DeploymentStoreConfig,
    ServerType,
)


class ServerDockerComposeMariaDBTestDeployment(BaseTestDeployment):
    """A deployment that runs a ZenML server and MariaDB DB as docker containers using docker-compose."""

    @staticmethod
    def _generate_docker_compose_manifest() -> str:
        """Generates a docker-compose manifest for the deployment.

        Returns:
            The docker-compose manifest as a string.

        Raises:
            RuntimeError: If no available port could be found for the MariaDB
                container or the ZenML server.
        """
        from zenml.utils.networking_utils import scan_for_available_port

        # Generate a random port for the MariaDB container
        mariadb_port = scan_for_available_port(MARIADB_DEFAULT_PORT)
        if mariadb_port is None:
            raise RuntimeError("Could not find an available port for MariaDB.")

        zenml_port = scan_for_available_port(LOCAL_ZENML_SERVER_DEFAULT_PORT)
        if zenml_port is None:
            raise RuntimeError(
                "Could not find an available port for the ZenML server."
            )

        return f"""
version: "3.9"

services:
  mariadb:
    image: {MARIADB_DOCKER_IMAGE}
    ports:
      - {mariadb_port}:3306
    environment:
      - MARIADB_ROOT_PASSWORD={MARIADB_ROOT_PASSWORD}
    # Enable the primary key requirement for MariaDB to catch errors related to
    # missing primary keys.
    command:
      - --innodb-force-primary-key=1
  zenml:
    image: {ZENML_SERVER_IMAGE_NAME}
    ports:
      - "{zenml_port}:8080"
    environment:
      - ZENML_STORE_URL=mysql://root:{MARIADB_ROOT_PASSWORD}@host.docker.internal/zenml
      - ZENML_SERVER_DEPLOYMENT_TYPE=docker
      - ZENML_SERVER_AUTO_ACTIVATE=True
      - ZENML_SERVER_AUTO_CREATE_DEFAULT_USER=True
    links:
      - mariadb
    depends_on:
      - mariadb
    extra_hosts:
      - "host.docker.internal:host-gateway"
    restart: on-failure
"""

    @property
    def zenml_container_name(self) -> str:
        """The name of the ZenML container.

        Returns:
            The name of the ZenML container.
        """
        return f"{self.config.name}-zenml-1"

    @property
    def mariadb_container_name(self) -> str:
        """The name of the MariaDB container.

        Returns:
            The name of the MariaDB container.
        """
        return f"{self.config.name}-mariadb-1"

    @property
    def zenml_container(self) -> Optional[Container]:
        """Returns the Docker container running the ZenML server.

        Returns:
            The container for the ZenML server if it exists, None otherwise.
        """
        try:
            return self.docker_client.containers.get(self.zenml_container_name)
        except docker_errors.NotFound:
            return None

    @property
    def mariadb_container(self) -> Optional[Container]:
        """Returns the Docker container running the MariaDB server.

        Returns:
            The container for the MariaDB server if it exists, None otherwise.
        """
        try:
            return self.docker_client.containers.get(
                self.mariadb_container_name
            )
        except docker_errors.NotFound:
            return None

    @property
    def is_running(self) -> bool:
        """Returns whether the deployment is running.

        Returns:
            True if the deployment is running, False otherwise.
        """
        zenml_container = self.zenml_container
        if zenml_container is None or zenml_container.status != "running":
            return False

        mariadb_container = self.mariadb_container
        if mariadb_container is None or mariadb_container.status != "running":
            return False

        return True

    def up(self) -> None:
        """Starts the deployment.

        Raises:
            RuntimeError: If the deployment could not be started.
        """
        from docker_composer_v2 import (  # type: ignore[attr-defined]
            DockerCompose,
        )

        if self.is_running:
            logging.info(
                f"Deployment '{self.config.name}' is already running. "
                f"Skipping provisioning."
            )
            return

        manifest = self._generate_docker_compose_manifest()
        path = self.get_home_path()
        path.mkdir(parents=True, exist_ok=True)
        manifest_path = path / "docker-compose.yml"
        # write manifest to a file in the deployment root path
        with open(manifest_path, "w") as f:
            f.write(manifest)

        self.build_server_image()

        DockerCompose(
            file=str(manifest_path), project_name=self.config.name
        ).up(
            wait=True,
            pull="missing",
            no_deps=False,
            abort_on_container_exit=False,
            # "SERVICE": "",
            remove_orphans=False,
            no_recreate=False,
            force_recreate=True,
            always_recreate_deps=True,
            build=False,
            no_build=False,
            no_color=False,
            detach=True,
            # scale="",
            no_log_prefix=False,
        ).call(capture_output=True, check=True)

        timeout = DEPLOYMENT_START_TIMEOUT
        while True:
            logging.info(
                f"Trying to connect to deployment '{self.config.name}'..."
            )
            try:
                with self.connect() as client:
                    _ = client.zen_store
                    break
            except RuntimeError as e:
                timeout -= 1
                if timeout == 0:
                    raise RuntimeError(
                        f"Timed out waiting for the '{self.config.name}' "
                        f"deployment to start: {e}"
                    ) from e
                time.sleep(1)

        logging.info(
            f"Started docker-compose project '{self.config.name}' "
            f"for deployment '{self.config.name}'."
        )

    def down(self) -> None:
        """Stops the deployment."""
        from docker_composer_v2 import (  # type: ignore[attr-defined]
            DockerCompose,
        )

        zenml_container = self.zenml_container
        mariadb_container = self.mariadb_container
        if zenml_container is None and mariadb_container is None:
            logging.info(
                f"Deployment '{self.config.name}' is no longer running. "
            )
            return

        path = self.get_home_path()
        manifest_path = path / "docker-compose.yml"

        DockerCompose(
            file=str(manifest_path), project_name=self.config.name
        ).down(
            remove_orphans=False,
            volumes="",
        ).call(capture_output=True, check=True)

        logging.info(
            f"Removed docker-compose project '{self.config.name}' "
            f"for deployment '{self.config.name}'."
        )

    def get_store_config(self) -> Optional[DeploymentStoreConfig]:
        """Returns the store config for the deployment.

        Returns:
            The store config for the deployment if it is running, None
            otherwise.

        Raises:
            RuntimeError: If the deployment is not running.
        """
        from zenml.constants import (
            DEFAULT_PASSWORD,
            DEFAULT_USERNAME,
        )

        if not self.is_running:
            raise RuntimeError(
                f"The {self.config.name} deployment is not running."
            )

        container = self.zenml_container
        assert container is not None
        try:
            port = int(container.ports[f"{8080}/tcp"][0]["HostPort"])
        except (KeyError, IndexError):
            raise RuntimeError(
                f"Could not find the port for the '{self.config.name}' "
                f"deployment."
            )

        return DeploymentStoreConfig(
            url=f"http://127.0.0.1:{port}",
            username=DEFAULT_USERNAME,
            password=DEFAULT_PASSWORD,
        )


ServerDockerComposeMariaDBTestDeployment.register_deployment_class(
    server_type=ServerType.DOCKER, database_type=DatabaseType.MARIADB
)
