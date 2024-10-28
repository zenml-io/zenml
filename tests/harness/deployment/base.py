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
"""Base ZenML deployment."""

import logging
import os
import sys
from abc import ABC, abstractmethod
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Generator, Optional, Tuple, Type

from docker.client import DockerClient

import zenml
from tests.harness.model import (
    DatabaseType,
    DeploymentConfig,
    DeploymentStoreConfig,
    ServerType,
)
from zenml.constants import ENV_ZENML_CONFIG_PATH
from zenml.enums import StoreType

if TYPE_CHECKING:
    from zenml.client import Client

LOCAL_ZENML_SERVER_DEFAULT_PORT = 9000
MYSQL_DOCKER_IMAGE = "mysql:8.0"
MYSQL_DEFAULT_PASSWORD = "zenml"
MYSQL_DEFAULT_PORT = 3306
MARIADB_DOCKER_IMAGE = "mariadb:10.6"
MARIADB_ROOT_PASSWORD = "zenml"
MARIADB_DEFAULT_PORT = 3306
ZENML_SERVER_IMAGE_NAME = "localhost/zenml-server"
ZENML_IMAGE_NAME = (
    f"zenmldocker/zenml:{zenml.__version__}-"
    f"py{sys.version_info.major}.{sys.version_info.minor}"
)
DEFAULT_DEPLOYMENT_ROOT_DIR = "zenml-test"
ENV_DEPLOYMENT_ROOT_PATH = "ZENML_TEST_DEPLOYMENT_ROOT_PATH"
DEPLOYMENT_START_TIMEOUT = 60


class BaseTestDeployment(ABC):
    """Base class for ZenML test deployments."""

    DEPLOYMENTS: Dict[
        Tuple[ServerType, DatabaseType], Type["BaseTestDeployment"]
    ] = {}

    def __init__(self, config: DeploymentConfig) -> None:
        """Initializes the deployment.

        Args:
            config: The configuration for the deployment.
        """
        self.config = config
        self._docker_client: Optional[DockerClient] = None

    @classmethod
    def register_deployment_class(
        cls, server_type: ServerType, database_type: DatabaseType
    ) -> None:
        """Registers the deployment in the global registry.

        Args:
            server_type: The server deployment type.
            database_type: The database deployment type.

        Raises:
            ValueError: If a deployment class is already registered for the
                given server and database types.
        """
        if cls.get_deployment_class(server_type, database_type) is not None:
            raise ValueError(
                f"Deployment class for type '{server_type}' and setup "
                f"'{database_type}' already registered"
            )
        BaseTestDeployment.DEPLOYMENTS[(server_type, database_type)] = cls

    @classmethod
    def get_deployment_class(
        cls, server_type: ServerType, database_type: DatabaseType
    ) -> Optional[Type["BaseTestDeployment"]]:
        """Returns the deployment class for the given server and database types.

        Args:
            server_type: The server deployment type.
            database_type: The database deployment type.

        Returns:
            The deployment class registered for the given server and database
            types, if one exists.
        """
        return cls.DEPLOYMENTS.get((server_type, database_type))

    @classmethod
    def from_config(cls, config: DeploymentConfig) -> "BaseTestDeployment":
        """Creates a deployment from a deployment config.

        Args:
            config: The deployment config.

        Returns:
            The deployment instance.

        Raises:
            ValueError: If no deployment class is registered for the given
                deployment type and setup method.
        """
        deployment_class = cls.get_deployment_class(
            config.server, config.database
        )
        if deployment_class is None:
            raise ValueError(
                f"No deployment class registered for type '{config.server}' "
                f"and setup '{config.database}'"
            )
        return deployment_class(config)

    @property
    @abstractmethod
    def is_running(self) -> bool:
        """Returns whether the deployment is running.

        Returns:
            Whether the deployment is running.
        """

    @abstractmethod
    def up(self) -> None:
        """Starts up the deployment."""

    @abstractmethod
    def down(self) -> None:
        """Tears down the deployment."""

    @abstractmethod
    def get_store_config(self) -> Optional[DeploymentStoreConfig]:
        """Returns the client store configuration needed to connect to the deployment.

        Returns:
           The store configuration, if one is required to connect to the
           deployment.
        """

    def cleanup(self) -> None:
        """Tears down the deployment and cleans up all local files."""
        from tests.harness.utils import cleanup_folder

        self.down()

        runtime_path = self.get_runtime_path()
        if not runtime_path.exists():
            return

        cleanup_folder(str(runtime_path))

    @property
    def docker_client(self) -> DockerClient:
        """Returns the docker client.

        Returns:
            The docker client.

        Raises:
            RuntimeError: If Docker is not installed or running on the machine.
        """
        if self._docker_client is None:
            try:
                # Try to ping Docker, to see if it's installed and running
                docker_client = DockerClient.from_env()
                docker_client.ping()
                self._docker_client = docker_client
            except Exception as e:
                raise RuntimeError(
                    "Docker is not installed or running on this machine",
                ) from e

        return self._docker_client

    @staticmethod
    def build_server_image() -> None:
        """Builds the server image locally."""
        from zenml.utils.docker_utils import build_image

        logging.info(
            f"Building ZenML server image '{ZENML_SERVER_IMAGE_NAME}' locally"
        )

        context_root = Path(__file__).parents[3]
        docker_file_path = (
            context_root / "docker" / "zenml-server-dev.Dockerfile"
        )
        build_image(
            image_name=ZENML_SERVER_IMAGE_NAME,
            dockerfile=str(docker_file_path),
            build_context_root=str(context_root),
            platform="linux/amd64",
        )

    @staticmethod
    def build_base_image() -> None:
        """Builds the base image locally."""
        from zenml.utils.docker_utils import build_image

        logging.info(f"Building ZenML base image '{ZENML_IMAGE_NAME}' locally")

        context_root = Path(__file__).parents[3]
        docker_file_path = context_root / "docker" / "zenml-dev.Dockerfile"
        build_image(
            image_name=ZENML_IMAGE_NAME,
            dockerfile=str(docker_file_path),
            build_context_root=str(context_root),
            platform="linux/amd64",
            # Use the same Python version as the current environment
            buildargs={
                "PYTHON_VERSION": f"{sys.version_info.major}.{sys.version_info.minor}"
            },
        )

    @classmethod
    def get_root_path(cls) -> Path:
        """Returns the root path used for test deployments.

        Returns:
            The root path for test deployments.
        """
        import click

        if ENV_DEPLOYMENT_ROOT_PATH in os.environ:
            return Path(os.environ[ENV_DEPLOYMENT_ROOT_PATH]).resolve()

        return Path(click.get_app_dir(DEFAULT_DEPLOYMENT_ROOT_DIR)).resolve()

    def get_runtime_path(self) -> Path:
        """Returns the runtime path used for the deployment.

        Returns:
            The runtime path for the deployment.
        """
        return self.get_root_path() / self.config.name

    def global_config_path(self) -> Path:
        """Returns the global config path used for the deployment.

        Returns:
            The global config path for the deployment.
        """
        return self.get_runtime_path() / ".zenconfig"

    @contextmanager
    def connect(
        self,
        global_config_path: Optional[Path] = None,
        custom_username: Optional[str] = None,
        custom_password: Optional[str] = None,
    ) -> Generator["Client", None, None]:
        """Context manager to create a client and connect it to the deployment.

        Call this method to configure zenml to connect to this deployment,
        run some code in the context of this configuration and then
        switch back to the previous configuration.

        Args:
            global_config_path: Custom global config path. If not provided,
                the global config path where the deployment is provisioned
                is used.
            custom_username: Custom username to use for the connection.
            custom_password: Custom password to use for the connection.

        Yields:
            A ZenML Client configured to connect to this deployment.

        Raises:
            RuntimeError: If the deployment is disabled.
        """
        from zenml.client import Client
        from zenml.config.global_config import GlobalConfiguration
        from zenml.config.store_config import StoreConfiguration
        from zenml.login.credentials_store import CredentialsStore
        from zenml.zen_stores.base_zen_store import BaseZenStore

        if self.config.disabled:
            raise RuntimeError(
                "Cannot connect to a disabled deployment. "
                "Please enable the deployment in the configuration first."
            )

        # set the ZENML_CONFIG_PATH environment variable to ensure that the
        # deployment uses a config isolated from the main config
        config_path = global_config_path or self.global_config_path()
        if not config_path.exists():
            config_path.mkdir(parents=True)

        # save the current global configuration and client singleton instances
        # to restore them later, then reset them
        original_config = GlobalConfiguration.get_instance()
        original_client = Client.get_instance()
        orig_config_path = os.getenv(ENV_ZENML_CONFIG_PATH)
        original_credentials = CredentialsStore.get_instance()

        CredentialsStore.reset_instance()
        GlobalConfiguration._reset_instance()
        Client._reset_instance()

        os.environ[ENV_ZENML_CONFIG_PATH] = str(config_path)
        os.environ["ZENML_ANALYTICS_OPT_IN"] = "false"
        os.environ["ZENML_ENABLE_REPO_INIT_WARNINGS"] = "false"
        os.environ["ZENML_DISABLE_WORKSPACE_WARNINGS"] = "true"

        # initialize the global config and client at the new path
        gc = GlobalConfiguration()
        gc.analytics_opt_in = False

        store_config = self.get_store_config()
        if store_config is not None:
            store_type = BaseZenStore.get_store_type(store_config.url)
            store_config_dict = store_config.model_dump()
            if store_type == StoreType.REST:
                if custom_username is not None:
                    store_config_dict["username"] = custom_username
                if custom_password is not None:
                    store_config_dict["password"] = custom_password
            gc.store = StoreConfiguration(
                type=store_type,
                **store_config_dict,
            )

        client = Client()

        yield client

        # restore the global configuration path
        if orig_config_path:
            os.environ[ENV_ZENML_CONFIG_PATH] = orig_config_path
        else:
            del os.environ[ENV_ZENML_CONFIG_PATH]

        # restore the global configuration, the client and the credentials store
        GlobalConfiguration._reset_instance(original_config)
        Client._reset_instance(original_client)
        CredentialsStore.reset_instance(original_credentials)
