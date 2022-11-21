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
"""Service for ZenML Stack Recipes."""

import os
import subprocess
from typing import Any, ClassVar, Dict, Optional, cast

import yaml

import zenml
from zenml.cli.stack_recipes import logger
from zenml.services import ServiceType
from zenml.services.terraform.terraform_service import (
    SERVICE_CONFIG_FILE_NAME,
    TerraformService,
)
from zenml.utils import io_utils, yaml_utils

STACK_FILE_NAME_OUTPUT = "stack-yaml-path"
DATABASE_HOST_OUTPUT = "metadata-db-host"
DATABASE_USERNAME_OUTPUT = "metadata-db-username"
DATABASE_PASSWORD_OUTPUT = "metadata-db-password"
INGRESS_CONTROLLER_HOST_OUTPUT = "ingress-controller-host"
PROJECT_ID_OUTPUT = "project-id"
ZENML_VERSION_VARIABLE = "zenml-version"


class StackRecipeService(TerraformService):
    """Class to represent terraform applications."""

    SERVICE_TYPE = ServiceType(
        name="stackrecipes",
        description="Stack recipe service",
        type="terraform",
        flavor="recipes",
    )

    STACK_RECIPES_CONFIG_PATH: ClassVar[str] = os.path.join(
        io_utils.get_global_config_directory(),
        "stack_recipes",
    )

    create_zen_server: bool = False

    def check_installation(self) -> None:
        """Checks if necessary tools are installed on the host system.

        Raises:
            RuntimeError: if any required tool is not installed.
        """
        super().check_installation()

        if not self._is_kubectl_installed():
            raise RuntimeError(
                "kubectl is not installed on your machine or not available on  "
                "your $PATH. It is used by stack recipes to create some "
                "resources on Kubernetes and to configure access to your "
                "cluster. Please visit "
                "https://kubernetes.io/docs/tasks/tools/#kubectl "
                "to install it."
            )
        if not self._is_helm_installed():
            raise RuntimeError(
                "Helm is not installed on your machine or not available on  "
                "your $PATH. It is required for stack recipes to create releases "
                "on Kubernetes. Please visit "
                "https://helm.sh/docs/intro/install/ "
                "to install it."
            )
        if not self._is_docker_installed():
            raise RuntimeError(
                "Docker is not installed on your machine or not available on  "
                "your $PATH. It is required for stack recipes to configure "
                "access to the container registry. Please visit "
                "https://docs.docker.com/engine/install/ "
                "to install it."
            )

    def _is_kubectl_installed(self) -> bool:
        """Checks if kubectl is installed on the host system.

        Returns:
            True if kubectl is installed, false otherwise.
        """
        try:
            subprocess.check_output(["kubectl"])
        except subprocess.CalledProcessError:
            return False

        return True

    def _is_helm_installed(self) -> bool:
        """Checks if helm is installed on the host system.

        Returns:
            True if helm is installed, false otherwise.
        """
        try:
            subprocess.check_output(["helm", "version"])
        except subprocess.CalledProcessError:
            return False

        return True

    def _is_docker_installed(self) -> bool:
        """Checks if docker is installed on the host system.

        Returns:
            True if docker is installed, false otherwise.
        """
        try:
            subprocess.check_output(["docker", "--version"])
        except subprocess.CalledProcessError:
            return False

        return True

    @property
    def stack_file_path(self) -> str:
        """Get the path to the stack yaml file.

        Returns:
            The path to the stack yaml file.
        """
        # return the path of the stack yaml file
        stack_file_path = self.terraform_client.output(
            STACK_FILE_NAME_OUTPUT, full_value=True
        )
        return str(stack_file_path)

    @classmethod
    def get_service(cls, recipe_path: str) -> Optional["StackRecipeService"]:
        """Load and return the stack recipe service, if present.

        Args:
            recipe_path: The path to the directory that hosts the recipe.

        Returns:
            The stack recipe service or None, if the stack recipe
            deployment is not found.
        """
        from zenml.services import ServiceRegistry

        try:
            for root, _, files in os.walk(str(cls.STACK_RECIPES_CONFIG_PATH)):
                for file in files:
                    if file == SERVICE_CONFIG_FILE_NAME:
                        service_config_path = os.path.join(root, file)
                        logger.debug(
                            "Loading service daemon configuration from %s",
                            service_config_path,
                        )
                        service_config = None
                        with open(service_config_path, "r") as f:
                            service_config = f.read()
                        stack_recipe_service = cast(
                            StackRecipeService,
                            ServiceRegistry().load_service_from_json(
                                service_config
                            ),
                        )
                        if (
                            stack_recipe_service.config.directory_path
                            == recipe_path
                        ):
                            return stack_recipe_service
            return None
        except FileNotFoundError:
            return None

    def get_vars(self) -> Dict[str, Any]:
        """Get variables as a dictionary.

        Returns:
            A dictionary of variables to use for the stack recipes
            derived from the tfvars.json file.
        """
        vars = super().get_vars()
        # update zenml version to current version
        vars[ZENML_VERSION_VARIABLE] = zenml.__version__
        return vars

    def get_deployment_info(self) -> str:
        """Return deployment details as a YAML document.

        Returns:
            A YAML document that can be passed as config to
            the server deploy function.
        """
        provider = yaml_utils.read_yaml(
            file_path=os.path.join(
                self.terraform_client.working_dir, "metadata.yaml"
            )
        )["Cloud"]

        config = {
            "name": f"{provider}",
            "provider": f"{provider}",
            "deploy_db": True,
            "create_ingress_controller": False,
            "ingress_controller_hostname": self.terraform_client.output(
                INGRESS_CONTROLLER_HOST_OUTPUT, full_value=True
            ),
        }

        if provider == "gcp":
            config["project_id"] = self.terraform_client.output(
                PROJECT_ID_OUTPUT, full_value=True
            )

        return cast(str, yaml.dump(config))
