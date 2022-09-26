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
from typing import Any, Optional, Tuple, cast

from zenml.logger import get_logger
from zenml.services import (
    ServiceState,
    ServiceType,
    TerraformService,
    TerraformServiceConfig,
)
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
TERRAFORM_ZENML_SERVER_RECIPE_ROOT_PATH = (
    "/mnt/w/apps/zenml/terraform_zenml_server"
)
TERRAFORM_VALUES_FILE_PATH = "values.tfvars.json"
TERRAFORM_DEPLOYED_ZENSERVER_URL_OUTPUT = "zenml_server_url"

TERRAFORM_ZENML_SERVER_DEFAULT_TIMEOUT = 60


class TerraformServerDeploymentConfig(ServerDeploymentConfig):
    """Terraform server deployment configuration.

    Attributes:
        log_level: the log level to set the terraform client to. Choose one of
            TRACE, DEBUG, INFO, WARN or ERROR (case insensitive).
    """

    log_level: str = "ERROR"

    class Config:
        """Pydantic configuration."""

        extra = "forbid"


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

    def check_status(self) -> Tuple[ServiceState, str]:
        """Check the the current operational state of the terraform deployment.

        Returns:
            The operational state of the terraform deployment and a message
            providing additional information about that state (e.g. a
            description of the error, if one is encountered).

        Raises:
            NotImplementedError: not implemented.
        """
        raise NotImplementedError(
            "This method is not available for Terraform recipes."
        )

    def _copy_config_values(self) -> None:
        """Copy values from the server config to the locals.tf file."""
        # get the contents of the values.tfvars.json file as a dictionary
        variables = self.get_vars(self.config.directory_path)

        # get the contents of the server deploymen config as dict
        server_config = self.config.server.dict()

        # update the variables dict with values from the server
        # deployment config
        for key in server_config.keys() & variables.keys():
            variables[key] = server_config[key]

        self._write_to_variables_file(variables)

    def _write_to_variables_file(self, variables: Any) -> None:
        """Write the dictionary into the values.tfvars.json file.

        Args:
            variables: the variables dict with the user-provided
            config values
        """
        import json

        with open(
            os.path.join(
                self.config.directory_path, self.config.variables_file_path
            ),
            "w",
        ) as fp:
            json.dump(variables, fp=fp)

    def provision(self) -> None:
        """Provision the service."""
        self._copy_config_values()
        super().provision()
        zenml_server_url = self._get_server_url()
        if zenml_server_url == "":
            logger.info(
                "It looks like you chose not to deploy an ingress "
                "controller through ZenML. You can access ZenML "
                "at the URL for your controller with a path you "
                "configured while deploying ZenML (default: /zenml)."
            )
        else:
            logger.info(
                f"Your ZenML server is now deployed on AWS with URL:\n"
                f"${zenml_server_url}"
            )

    def _get_server_url(self) -> str:
        """Returns the deployed ZenML server's URL"""
        return self.terraform_client.output(
            TERRAFORM_DEPLOYED_ZENSERVER_URL_OUTPUT, full_value=True
        )
