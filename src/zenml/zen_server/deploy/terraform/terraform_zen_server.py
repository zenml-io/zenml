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

from zenml.enums import TerraformZenServerType
from zenml.logger import get_logger
from zenml.services import ServiceType, TerraformService, TerraformServiceConfig
from zenml.services.container.container_service import (
    SERVICE_CONTAINER_GLOBAL_CONFIG_DIR,
)
from zenml.utils.io_utils import get_global_config_directory
from zenml.zen_server.deploy.deployment import ServerDeploymentConfig

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
TERRAFORM_ZENML_SERVER_RECIPE_ROOT_PATH = "path to terraform_zenml_server"
TERRAFORM_VALUES_FILE_PATH = "values.tfvars.json"

TERRAFORM_ZENML_SERVER_DEFAULT_TIMEOUT = 60


class TerraformServerDeploymentConfig(ServerDeploymentConfig):
    """Terraform server deployment configuration.

    Attributes:
        log_level: the log level to set the terraform client to. Choose one of
            TRACE, DEBUG, INFO, WARN or ERROR (case insensitive).
    """

    type: TerraformZenServerType
    log_level: str = "ERROR"


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
