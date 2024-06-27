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

from pydantic import ConfigDict

import zenml
from zenml.config.global_config import GlobalConfiguration
from zenml.config.store_config import StoreConfiguration
from zenml.constants import (
    DEFAULT_ZENML_SERVER_USE_LEGACY_DASHBOARD,
    ENV_ZENML_ANALYTICS_OPT_IN,
    ENV_ZENML_CONFIG_PATH,
    ENV_ZENML_DISABLE_DATABASE_MIGRATION,
    ENV_ZENML_LOCAL_STORES_PATH,
    ENV_ZENML_SERVER_AUTO_ACTIVATE,
    ENV_ZENML_SERVER_DEPLOYMENT_TYPE,
    ENV_ZENML_SERVER_USE_LEGACY_DASHBOARD,
    LOCAL_STORES_DIRECTORY_NAME,
    ZEN_SERVER_ENTRYPOINT,
)
from zenml.enums import StoreType
from zenml.logger import get_logger
from zenml.models import ServerDeploymentType
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
    use_legacy_dashboard: bool = DEFAULT_ZENML_SERVER_USE_LEGACY_DASHBOARD

    model_config = ConfigDict(extra="forbid")


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

    @classmethod
    def get_service(cls) -> Optional["DockerZenServer"]:
        """Load and return the docker ZenML server service, if present.

        Returns:
            The docker ZenML server service or None, if the docker server
            deployment is not found.
        """
        config_filename = os.path.join(cls.config_path(), "service.json")
        try:
            with open(config_filename, "r") as f:
                return cast(
                    "DockerZenServer", DockerZenServer.from_json(f.read())
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
        gc = GlobalConfiguration()

        cmd, env = super()._get_container_cmd()
        env[ENV_ZENML_CONFIG_PATH] = os.path.join(
            SERVICE_CONTAINER_PATH,
            SERVICE_CONTAINER_GLOBAL_CONFIG_DIR,
        )
        env[ENV_ZENML_SERVER_DEPLOYMENT_TYPE] = ServerDeploymentType.DOCKER
        env[ENV_ZENML_ANALYTICS_OPT_IN] = str(gc.analytics_opt_in)

        # Set the local stores path to the same path used by the client (mounted
        # in the container by the super class). This ensures that the server's
        # default store configuration is initialized to point at the same local
        # SQLite database as the client.
        env[ENV_ZENML_LOCAL_STORES_PATH] = os.path.join(
            SERVICE_CONTAINER_GLOBAL_CONFIG_PATH,
            LOCAL_STORES_DIRECTORY_NAME,
        )
        env[ENV_ZENML_DISABLE_DATABASE_MIGRATION] = "True"
        env[ENV_ZENML_SERVER_USE_LEGACY_DASHBOARD] = str(
            self.config.server.use_legacy_dashboard
        )
        env[ENV_ZENML_SERVER_AUTO_ACTIVATE] = "True"

        return cmd, env

    def provision(self) -> None:
        """Provision the service."""
        super().provision()

    def run(self) -> None:
        """Run the ZenML Server.

        Raises:
            ValueError: if started with a global configuration that connects to
                another ZenML server.
        """
        import uvicorn

        gc = GlobalConfiguration()
        if gc.store_configuration.type == StoreType.REST:
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
                host="0.0.0.0",  # nosec
                port=self.endpoint.config.port or 8000,
                log_level="info",
                server_header=False,
            )
        except KeyboardInterrupt:
            logger.info("ZenML Server stopped. Resuming normal execution.")
