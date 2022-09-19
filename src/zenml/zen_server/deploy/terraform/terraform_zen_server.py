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
"""Service implementation for the ZenML terraform server deployment."""

import os
from typing import Optional, cast

from zenml.config.global_config import GlobalConfiguration
from zenml.logger import get_logger
from zenml.services import ServiceType, TerraformService, TerraformServiceConfig
from zenml.services.container.container_service import (
    SERVICE_CONTAINER_GLOBAL_CONFIG_DIR,
    SERVICE_CONTAINER_GLOBAL_CONFIG_PATH,
)
from zenml.utils.io_utils import get_global_config_directory
from zenml.zen_server.deploy.deployment import ServerDeploymentConfig
from zenml.zen_stores.sql_zen_store import SqlZenStore

logger = get_logger(__name__)

ZEN_SERVER_HEALTHCHECK_URL_PATH = "health"

TERRAFORM_ZENML_SERVER_CONFIG_SUBPATH = os.path.join(
    "zen_server",
    "terraform",
)

TERRAFORM_ZENML_SERVER_CONFIG_PATH = os.path.join(
    get_global_config_directory(),
    TERRAFORM_ZENML_SERVER_CONFIG_SUBPATH,
)
TERRAFORM_ZENML_SERVER_CONFIG_FILENAME = os.path.join(
    TERRAFORM_ZENML_SERVER_CONFIG_PATH, "service.json"
)
TERRAFORM_ZENML_SERVER_GLOBAL_CONFIG_PATH = os.path.join(
    TERRAFORM_ZENML_SERVER_CONFIG_PATH, SERVICE_CONTAINER_GLOBAL_CONFIG_DIR
)
TERRAFORM_ZENML_SERVER_DEFAULT_IMAGE = "zenmlterraform/zenml-server"

TERRAFORM_ZENML_SERVER_DEFAULT_TIMEOUT = 60


class TerraformServerDeploymentConfig(ServerDeploymentConfig):
    """Terraform server deployment configuration.

    Attributes:
        directory_path: the path to the directory that hosts all the HCL files.
        log_level: the log level to set the terraform client to. Choose one of
            TRACE, DEBUG, INFO, WARN or ERROR (case insensitive).
        variables_file_path: the path to the file that stores all variable values.
    """

    directory_path: str
    log_level: str = "ERROR"
    variables_file_path: str = "values.tfvars.json"


class TerraformZenServerConfig(TerraformServiceConfig):
    """Terraform Zen server configuration.

    Attributes:
        server: The deployment configuration.
    """

    server: TerraformServerDeploymentConfig


class TerraformZenServer(TerraformService):
    """Service that can be used to start a terraform ZenServer.

    Attributes:
        config: service configuration
        endpoint: service endpoint
    """

    SERVICE_TYPE = ServiceType(
        name="terraform_zenml_server",
        type="zen_server",
        flavor="terraform",
        description="Terraform ZenML server deployment",
    )

    config: TerraformZenServerConfig

    def _copy_global_configuration(self) -> None:
        """Copy the global configuration to the terraform ZenML server location.

        The terraform ZenML server global configuration is a copy of the terraform
        global configuration with the store configuration set to point to the
        local store.
        """
        gc = GlobalConfiguration()

        # this creates a copy of the global configuration with the store
        # set to where the default local store is mounted in the terraform
        # container and saves it to the server configuration path
        store_config = gc.get_default_store()
        store_config.url = SqlZenStore.get_local_url(
            SERVICE_CONTAINER_GLOBAL_CONFIG_PATH
        )
        gc.copy_configuration(
            config_path=TERRAFORM_ZENML_SERVER_GLOBAL_CONFIG_PATH,
            store_config=store_config,
        )

    @classmethod
    def get_service(cls) -> Optional["TerraformZenServer"]:
        """Load and return the terraform ZenML server service, if present.

        Returns:
            The terraform ZenML server service or None, if the terraform server
            deployment is not found.
        """
        from zenml.services import ServiceRegistry

        try:
            with open(TERRAFORM_ZENML_SERVER_CONFIG_FILENAME, "r") as f:
                return cast(
                    TerraformZenServer,
                    ServiceRegistry().load_service_from_json(f.read()),
                )
        except FileNotFoundError:
            return None

    def provision(self) -> None:
        """Provision the service."""
        self._copy_global_configuration()
        super().provision()
