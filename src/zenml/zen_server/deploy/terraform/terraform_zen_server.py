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
from typing import Any, Dict, Optional, Tuple, cast

from pathlib import Path

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
TERRAFORM_ZENML_SERVER_RECIPE_SUBPATH = "recipes"
TERRAFORM_VALUES_FILE_PATH = "values.tfvars.json"
TERRAFORM_DEPLOYED_ZENSERVER_OUTPUT_URL = "zenml_server_url"
TERRAFORM_DEPLOYED_ZENSERVER_OUTPUT_TLS_CRT = "tls_crt"
TERRAFORM_DEPLOYED_ZENSERVER_OUTPUT_TLS_KEY = "tls_key"
TERRAFORM_DEPLOYED_ZENSERVER_OUTPUT_CA_CRT = "ca_crt"

TERRAFORM_ZENML_SERVER_DEFAULT_TIMEOUT = 60


ZENML_HELM_CHART_SUBPATH = "helm"


def get_helm_chart_path() -> str:
    """Get the ZenML server helm chart path.

    The ZenML server helm chart files are located in a folder relative to the
    `zenml.zen_server.deploy` Python module.

    Returns:
        The helm chart path.
    """
    import zenml.zen_server.deploy as deploy_module

    path = os.path.join(
        os.path.dirname(deploy_module.__file__),
        ZENML_HELM_CHART_SUBPATH,
    )
    return path


class TerraformServerDeploymentConfig(ServerDeploymentConfig):
    """Terraform server deployment configuration.

    Attributes:
        log_level: the log level to set the terraform client to. Choose one of
            TRACE, DEBUG, INFO, WARN or ERROR (case insensitive).
    """

    log_level: str = "ERROR"

    username: str
    password: str
    email: str = ""
    helm_chart: str = get_helm_chart_path()
    zenmlserver_namespace: str = "zenmlserver"
    kubectl_config_path: str = os.path.join(str(Path.home()), ".kube", "config")
    ingress_tls: bool = True
    ingress_tls_generate_certs: bool = True
    ingress_tls_secret_name: str = "zenml-tls-certs"
    rds_url: str = ""
    rds_sslCa: str = ""
    rds_sslCert: str = ""
    rds_sslKey: str = ""
    rds_sslVerifyServerCert: bool = True
    ingress_path: str = ""
    create_ingress_controller: bool = True
    ingress_controller_hostname: str = ""

    class Config:
        """Pydantic configuration."""

        extra = "allow"


class TerraformZenServerConfig(TerraformServiceConfig):
    """Terraform Zen server configuration.

    Attributes:
        server: The deployment configuration.
    """

    server: TerraformServerDeploymentConfig
    copy_terraform_files: bool = True


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

    def get_vars(self) -> Dict[str, Any]:
        """Get variables as a dictionary.

        Returns:
            A dictionary of variables to use for the Terraform deployment.
        """
        # get the contents of the server deployment config as dict
        filter_vars = ["log_level", "provider"]
        # filter keys that are not modeled as terraform deployment vars
        vars = {
            k: v
            for k, v in self.config.server.dict().items()
            if k not in filter_vars
        }
        self._write_to_variables_file(vars)
        return vars

    def _write_to_variables_file(self, variables: Dict[str, Any]) -> None:
        """Write the variables into the values.tfvars.json file.

        Args:
            variables: the variables dict with the user-provided
            config values
        """
        import json

        assert self.status.runtime_path
        with open(
            os.path.join(
                self.status.runtime_path, self.config.variables_file_path
            ),
            "w",
        ) as fp:
            json.dump(variables, fp=fp, indent=4)

    def provision(self) -> None:
        """Provision the service."""
        super().provision()
        logger.info(
            f"Your ZenML server is now deployed on AWS with URL:\n"
            f"${self.get_server_url()}"
        )

    def get_server_url(self) -> str:
        """Returns the deployed ZenML server's URL"""
        return str(
            self.terraform_client.output(
                TERRAFORM_DEPLOYED_ZENSERVER_OUTPUT_URL, full_value=True
            )
        )

    def get_certificate(self) -> Optional[str]:
        """Returns the CA certificates configured for the ZenML server."""
        return cast(
            str,
            self.terraform_client.output(
                TERRAFORM_DEPLOYED_ZENSERVER_OUTPUT_CA_CRT, full_value=True
            ),
        )
