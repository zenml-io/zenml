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
"""Service implementation for the ZenML docker server deployment."""

import os
from typing import Dict, List, Optional, Tuple, cast

import zenml
from zenml.config.global_config import GlobalConfiguration
from zenml.config.store_config import StoreConfiguration
from zenml.constants import (
    ENV_ZENML_CONFIG_PATH,
    ENV_ZENML_DISABLE_DATABASE_MIGRATION,
    ENV_ZENML_LOCAL_STORES_PATH,
    ENV_ZENML_SERVER_DEPLOYMENT_TYPE,
    LOCAL_STORES_DIRECTORY_NAME,
    ZEN_SERVER_ENTRYPOINT,
)
from zenml.enums import StoreType
from zenml.logger import get_logger
from zenml.models.server_models import ServerDeploymentType
from zenml.services import (
    ContainerService,
    ContainerServiceConfig,
    ContainerServiceEndpoint,
    ServiceType,
)
from zenml.services.container.container_service import (
    SERVICE_CONTAINER_GLOBAL_CONFIG_DIR,
    SERVICE_CONTAINER_GLOBAL_CONFIG_PATH,
    SERVICE_CONTAINER_PATH,
)
from zenml.utils.io_utils import get_global_config_directory
from zenml.zen_server.deploy.deployment import ServerDeploymentConfig

logger = get_logger(__name__)

ZEN_SERVER_HEALTHCHECK_URL_PATH = "health"
DOCKER_ZENML_SERVER_DEFAULT_IMAGE = (
    f"zenmldocker/zenml-server:{zenml.__version__}"
)
DOCKER_ZENML_SERVER_DEFAULT_TIMEOUT = 60


class DockerServerDeploymentConfig(ServerDeploymentConfig):
    """Docker server deployment configuration.

    Attributes:
        port: The TCP port number where the server is accepting connections.
        image: The Docker image to use for the server.
    """

    port: int = 8238
    image: str = DOCKER_ZENML_SERVER_DEFAULT_IMAGE
    store: Optional[StoreConfiguration] = None

    class Config:
        """Pydantic configuration."""

        extra = "forbid"


class DockerZenServerConfig(ContainerServiceConfig):
    """Docker Zen server configuration.

    Attributes:
        server: The deployment configuration.
    """

    server: DockerServerDeploymentConfig


class DockerZenServer(ContainerService):
    """Service that can be used to start a docker ZenServer.

    Attributes:
        config: service configuration
        endpoint: service endpoint
    """

    SERVICE_TYPE = ServiceType(
        name="docker_zenml_server",
        type="zen_server",
        flavor="docker",
        description="Docker ZenML server deployment",
    )

    config: DockerZenServerConfig
    endpoint: ContainerServiceEndpoint

    @classmethod
    def config_path(cls) -> str:
        """Path to the directory where the docker ZenML server files are located.

        Returns:
            Path to the docker ZenML server runtime directory.
        """
        return os.path.join(
            get_global_config_directory(),
            "zen_server",
            "docker",
        )

    @property
    def _global_config_path(self) -> str:
        """Path to the global configuration directory used by this server.

        Returns:
            Path to the global configuration directory used by this server.
        """
        return os.path.join(
            self.config_path(), SERVICE_CONTAINER_GLOBAL_CONFIG_DIR
        )

    def _copy_global_configuration(self) -> None:
        """Copy the global configuration to the docker ZenML server location.

        The docker ZenML server global configuration is a copy of the docker
        global configuration. If a store configuration is explicitly set in
        the server configuration, it will be used. Otherwise, the store
        configuration is set to point to the local store.
        """
        gc = GlobalConfiguration()

        # this creates a copy of the global configuration and saves it to the
        # server configuration path. The store is set to where the default local
        # store is mounted in the docker container unless a custom store
        # configuration is explicitly supplied with the server configuration.
        gc.copy_configuration(
            config_path=self._global_config_path,
            store_config=self.config.server.store,
            empty_store=self.config.server.store is None,
        )

    @classmethod
    def get_service(cls) -> Optional["DockerZenServer"]:
        """Load and return the docker ZenML server service, if present.

        Returns:
            The docker ZenML server service or None, if the docker server
            deployment is not found.
        """
        from zenml.services import ServiceRegistry

        config_filename = os.path.join(cls.config_path(), "service.json")
        try:
            with open(config_filename, "r") as f:
                return cast(
                    DockerZenServer,
                    ServiceRegistry().load_service_from_json(f.read()),
                )
        except FileNotFoundError:
            return None

    def _get_container_cmd(self) -> Tuple[List[str], Dict[str, str]]:
        """Get the command to run the service container.

        Override the inherited method to use a ZenML global config path inside
        the container that points to the global config copy instead of the
        one mounted from the local host.

        Returns:
            Command needed to launch the docker container and the environment
            variables to set, in the formats accepted by subprocess.Popen.
        """
        GlobalConfiguration()

        cmd, env = super()._get_container_cmd()
        env[ENV_ZENML_CONFIG_PATH] = os.path.join(
            SERVICE_CONTAINER_PATH,
            SERVICE_CONTAINER_GLOBAL_CONFIG_DIR,
        )
        env[ENV_ZENML_SERVER_DEPLOYMENT_TYPE] = ServerDeploymentType.DOCKER
        # Set the local stores path to point to where the client's local stores
        # path is mounted in the container. This ensures that the server's store
        # configuration is initialized with the same path as the client.
        env[ENV_ZENML_LOCAL_STORES_PATH] = os.path.join(
            SERVICE_CONTAINER_GLOBAL_CONFIG_PATH,
            LOCAL_STORES_DIRECTORY_NAME,
        )
        env[ENV_ZENML_DISABLE_DATABASE_MIGRATION] = "True"

        return cmd, env

    def provision(self) -> None:
        """Provision the service."""
        self._copy_global_configuration()
        super().provision()

    def run(self) -> None:
        """Run the ZenML Server.

        Raises:
            ValueError: if started with a global configuration that connects to
                another ZenML server.
        """
        import uvicorn  # type: ignore[import]

        gc = GlobalConfiguration()
        if gc.store and gc.store.type == StoreType.REST:
            raise ValueError(
                "The ZenML server cannot be started with REST store type."
            )
        logger.info(
            "Starting ZenML Server as blocking "
            "process... press CTRL+C once to stop it."
        )

        self.endpoint.prepare_for_start()

        try:
            uvicorn.run(
                ZEN_SERVER_ENTRYPOINT,
                host="0.0.0.0",
                port=self.endpoint.config.port,
                log_level="info",
            )
        except KeyboardInterrupt:
            logger.info("ZenML Server stopped. Resuming normal execution.")
