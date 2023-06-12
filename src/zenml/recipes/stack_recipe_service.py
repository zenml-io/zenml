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
import shutil
import subprocess
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Optional, cast

import yaml

import zenml
from zenml.exceptions import DoesNotExistException
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.recipes.git_stack_recipes_handler import (
    GitStackRecipesHandler,
)
from zenml.recipes.models import LocalStackRecipe
from zenml.services import ServiceType
from zenml.services.terraform.terraform_service import (
    SERVICE_CONFIG_FILE_NAME,
    TerraformService,
    TerraformServiceConfig,
)
from zenml.utils import io_utils, yaml_utils

logger = get_logger(__name__)

STACK_FILE_NAME_OUTPUT = "stack-yaml-path"
DATABASE_HOST_OUTPUT = "metadata-db-host"
DATABASE_USERNAME_OUTPUT = "metadata-db-username"
DATABASE_PASSWORD_OUTPUT = "metadata-db-password"
INGRESS_CONTROLLER_HOST_OUTPUT = "ingress-controller-host"
PROJECT_ID_OUTPUT = "project-id"
ZENML_VERSION_VARIABLE = "zenml-version"


class StackRecipeServiceConfig(TerraformServiceConfig):
    """Class to represent the configuration of a stack recipe service."""

    STACK_RECIPES_CONFIG_PATH: ClassVar[str] = os.path.join(
        io_utils.get_global_config_directory(),
        "stack_recipes",
    )

    # list of all enabled stack components
    enabled_services: List[str] = []
    # list of services to be disabled
    disabled_services: List[str] = []
    # input variables from the CLI
    input_variables: Dict[str, Any] = {}
    # root runtime path
    root_runtime_path: str = STACK_RECIPES_CONFIG_PATH
    # whether to skip pulling a recipe
    skip_pull: bool = False
    # whether to force pull a recipe before deploying
    force: bool = False


class StackRecipeService(TerraformService):
    """Class to represent terraform applications."""

    SERVICE_TYPE = ServiceType(
        name="stackrecipes",
        description="Stack recipe service",
        type="terraform",
        flavor="recipes",
    )

    config: StackRecipeServiceConfig
    stack_recipe_name: str

    def local_recipe_exists(self) -> bool:
        """Checks if the local recipe exists.

        Returns:
            Whether the local recipe exists.
        """
        local_stack_recipe = LocalStackRecipe(
            path=Path(self.config.directory_path), name=self.stack_recipe_name
        )
        return local_stack_recipe.is_present()

    def pull(
        self,
        git_stack_recipes_handler: GitStackRecipesHandler,
        force: bool = False,
    ) -> None:
        """Pulls the stack recipes from the main git stack recipes repository.

        Args:
            force: Whether to force the pull.
            git_stack_recipes_handler: The git stack recipes handler to use.

        Raises:
            DoesNotExistException: If the stack recipe does not exist locally.
        """
        if not self.local_recipe_exists():
            if self.config.skip_pull:
                raise DoesNotExistException(
                    "You have specified the --skip-pull flag, but the "
                    "stack recipe is not present locally at the specified "
                    f"path. Please ensure the {self.stack_recipe_name} recipe is "
                    f"present at {self.config.directory_path} and try again."
                )

        git_stack_recipes_handler.pull()

        if self.local_recipe_exists():
            if force:
                fileio.rmtree(self.config.directory_path)
            else:
                return

        logger.info(f"Pulling stack recipe {self.stack_recipe_name}...")

        io_utils.create_dir_recursive_if_not_exists(self.config.directory_path)
        stack_recipe = git_stack_recipes_handler.get_stack_recipes(
            self.stack_recipe_name
        )[0]
        git_stack_recipes_handler.copy_stack_recipe(
            stack_recipe, self.config.directory_path
        )
        logger.info(
            f"Stack recipe pulled in directory: {self.config.directory_path}"
        )
        logger.info(
            "\n Please edit the configuration values as you see fit, "
            f"in the file: {os.path.join(self.config.directory_path, 'locals.tf')} "
            "before you run the deploy command."
        )
        # also copy the modules folder from the repo (if it exists)
        # this is a temporary fix until we have a proper module registry
        modules_dir = os.path.join(
            git_stack_recipes_handler.stack_recipes_dir, "modules"
        )
        if os.path.exists(modules_dir):
            logger.info("Copying modules folder...")
            io_utils.copy_dir(
                modules_dir,
                os.path.join(
                    os.path.dirname(self.config.directory_path), "modules"
                ),
                True,
            )

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
            for root, _, files in os.walk(
                str(StackRecipeServiceConfig.STACK_RECIPES_CONFIG_PATH)
            ):
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

        # add input variables
        if self.config.input_variables:
            vars.update(self.config.input_variables)

        # enable services
        if self.config.enabled_services:
            for service in self.config.enabled_services:
                vars[f"enable_{service}"] = True
        # disable services
        elif self.config.disabled_services:
            for service in self.config.disabled_services:
                vars[f"enable_{service}"] = False

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

        return yaml.dump(config)

    @classmethod
    def get_version(cls) -> Optional[str]:
        """Get the version of the recipe.

        Returns:
            The version of the recipe.
        """
        handler = GitStackRecipesHandler()
        return handler.get_active_version()

    def provision(self) -> None:
        """Provision the service."""
        self.pull(git_stack_recipes_handler=GitStackRecipesHandler())
        super().provision()
        self.config.enabled_services = []
        self._update_service_config()

    def deprovision(self, force: bool = False) -> None:
        """Deprovision the service.

        Args:
            force: if True, the service will be deprovisioned even if it is
                in a failed state.
        """
        self.check_installation()
        self._set_log_level()

        # if a list of disabled services is provided, call apply
        # which will use the variables from get_vars and selectively
        # disable the services
        if self.config.disabled_services:
            self._init_and_apply()
            self.config.disabled_services = []
            self._update_service_config()
        else:
            # if no services are specified, destroy the whole stack
            # using the values of the existing tfvars.json file
            self._destroy()

            # in case of singleton services, this will remove the config
            # path as a whole and otherwise, this removes the specific UUID
            # directory
            assert self.status.config_file is not None
            shutil.rmtree(Path(self.status.config_file).parent)
