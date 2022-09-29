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

import ipaddress
import os
import shutil
from typing import Dict, List, Optional, Tuple, Union, cast

from zenml.config.global_config import GlobalConfiguration
from zenml.config.store_config import StoreConfiguration
from zenml.constants import (
    DEFAULT_LOCAL_SERVICE_IP_ADDRESS,
    ENV_ZENML_CONFIG_PATH,
    ENV_ZENML_SERVER_DEPLOYMENT_TYPE,
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
)
from zenml.services.container.entrypoint import SERVICE_CONTAINER_PATH
from zenml.utils.io_utils import get_global_config_directory
from zenml.zen_server.deploy.deployment import ServerDeploymentConfig
from zenml.zen_stores.sql_zen_store import SqlZenStore

logger = get_logger(__name__)

ZEN_SERVER_HEALTHCHECK_URL_PATH = "health"

DOCKER_ZENML_SERVER_CONFIG_SUBPATH = os.path.join(
    "zen_server",
    "docker",
)

DOCKER_ZENML_SERVER_CONFIG_PATH = os.path.join(
    get_global_config_directory(),
    DOCKER_ZENML_SERVER_CONFIG_SUBPATH,
)
DOCKER_ZENML_SERVER_CONFIG_FILENAME = os.path.join(
    DOCKER_ZENML_SERVER_CONFIG_PATH, "service.json"
)
DOCKER_ZENML_SERVER_GLOBAL_CONFIG_PATH = os.path.join(
    DOCKER_ZENML_SERVER_CONFIG_PATH, SERVICE_CONTAINER_GLOBAL_CONFIG_DIR
)
DOCKER_ZENML_SERVER_DEFAULT_IMAGE = "zenmldocker/zenml-server"

DOCKER_ZENML_SERVER_DEFAULT_TIMEOUT = 60


class DockerServerDeploymentConfig(ServerDeploymentConfig):
    """Docker server deployment configuration.

    Attributes:
        port: The TCP port number where the server is accepting connections.
        image: The Docker image to use for the server.
    """

    port: int = 8238
    image: str = DOCKER_ZENML_SERVER_DEFAULT_IMAGE
    address: Union[
        ipaddress.IPv4Address, ipaddress.IPv6Address
    ] = ipaddress.IPv4Address(DEFAULT_LOCAL_SERVICE_IP_ADDRESS)
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
        store_config = gc.get_default_store()
        store_config.url = SqlZenStore.get_local_url(
            SERVICE_CONTAINER_GLOBAL_CONFIG_PATH
        )
        gc.copy_configuration(
            config_path=DOCKER_ZENML_SERVER_GLOBAL_CONFIG_PATH,
            store_config=self.config.server.store or store_config,
        )

    @classmethod
    def get_service(cls) -> Optional["DockerZenServer"]:
        """Load and return the docker ZenML server service, if present.

        Returns:
            The docker ZenML server service or None, if the docker server
            deployment is not found.
        """
        from zenml.services import ServiceRegistry

        try:
            with open(DOCKER_ZENML_SERVER_CONFIG_FILENAME, "r") as f:
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
        cmd, env = super()._get_container_cmd()
        env[ENV_ZENML_CONFIG_PATH] = os.path.join(
            SERVICE_CONTAINER_PATH,
            SERVICE_CONTAINER_GLOBAL_CONFIG_DIR,
        )
        env[ENV_ZENML_SERVER_DEPLOYMENT_TYPE] = ServerDeploymentType.DOCKER
        return cmd, env

    def provision(self) -> None:
        """Provision the service."""
        self._copy_global_configuration()
        super().provision()

    def deprovision(self, force: bool = False) -> None:
        """Deprovision the service.

        Args:
            force: if True, the service daemon will be forcefully stopped
        """
        super().deprovision(force=force)
        shutil.rmtree(DOCKER_ZENML_SERVER_CONFIG_PATH)

    def run(self) -> None:
        """Run the ZenServer.

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
            "Starting ZenServer as blocking "
            "process... press CTRL+C once to stop it."
        )

        self.endpoint.prepare_for_start()

        try:
            uvicorn.run(
                ZEN_SERVER_ENTRYPOINT,
                host="0.0.0.0",  # self.endpoint.config.ip_address,
                port=self.endpoint.config.port,
                log_level="info",
            )
        except KeyboardInterrupt:
            logger.info("ZenServer stopped. Resuming normal execution.")
