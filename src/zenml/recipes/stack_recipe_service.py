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
from zenml.constants import STACK_RECIPES_GITHUB_REPO, STACK_RECIPES_REPO_DIR
from zenml.exceptions import DoesNotExistException, GitNotFoundError
from zenml.io import fileio
from zenml.logger import get_logger
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

EXCLUDED_RECIPE_DIRS = [""]


class LocalStackRecipe:
    """Class to encapsulate the local recipe that can be run from the CLI."""

    def __init__(self, path: Path, name: str) -> None:
        """Create a new LocalStack instance.

        Args:
            name: The name of the stack, specifically the name of the folder
                  on git
            path: Path at which the stack is installed
        """
        self.name = name
        self.path = path

    def is_present(self) -> bool:
        """Checks if the stack_recipe exists at the given path.

        Returns:
            True if the stack_recipe exists at the given path, else False.
        """
        return fileio.isdir(str(self.path))

    @property
    def locals_content(self) -> str:
        """Returns the locals.tf content associated with a particular recipe.

        Returns:
            The locals.tf content associated with a particular recipe.

        Raises:
            ValueError: If the locals.tf file is not found.
            FileNotFoundError: If the locals.tf file is not one of the options.
        """
        locals_file = os.path.join(self.path, "locals.tf")
        try:
            with open(locals_file) as locals:
                locals_content = locals.read()
            return locals_content
        except FileNotFoundError:
            if fileio.exists(str(self.path)) and fileio.isdir(str(self.path)):
                raise ValueError(f"No locals.tf file found in " f"{self.path}")
            else:
                raise FileNotFoundError(
                    f"Recipe {self.name} is not one of the available options."
                    f"\n"
                    f"To list all available recipes, type: `zenml stack recipe "
                    f"list`"
                )


class StackRecipe:
    """Class for all stack recipe objects."""

    def __init__(self, name: str, path_in_repo: Path) -> None:
        """Create a new StackRecipe instance.

        Args:
            name: The name of the recipe, specifically the name of the folder
                  on git
            path_in_repo: Path to the local recipe within the global zenml
                  folder.
        """
        self.name = name
        self.path_in_repo = path_in_repo

    @property
    def readme_content(self) -> str:
        """Returns the README content associated with a particular recipe.

        Returns:
            The README content associated with a particular recipe.

        Raises:
            ValueError: If the README file is not found.
            FileNotFoundError: If the README file is not one of the options.
        """
        readme_file = os.path.join(self.path_in_repo, "README.md")
        try:
            with open(readme_file) as readme:
                readme_content = readme.read()
            return readme_content
        except FileNotFoundError:
            if fileio.exists(str(self.path_in_repo)) and fileio.isdir(
                str(self.path_in_repo)
            ):
                raise ValueError(
                    f"No README.md file found in " f"{self.path_in_repo}"
                )
            else:
                raise FileNotFoundError(
                    f"Recipe {self.name} is not one of the available options."
                    f"\n"
                    f"To list all available recipes, type: `zenml stack recipe "
                    f"list`"
                )

    @property
    def metadata(self) -> Dict[str, Any]:
        """Returns the metadata associated with a particular recipe.

        Returns:
            The metadata associated with a particular recipe.
        """
        metadata = yaml_utils.read_yaml(
            file_path=os.path.join(self.path_in_repo, "metadata.yaml")
        )
        return cast(Dict[str, Any], metadata)


class StackRecipeRepo:
    """Class that represents the stack recipes repo."""

    def __init__(self, cloning_path: Path) -> None:
        """Create a new StackRecipeRepo instance.

        Args:
            cloning_path: Path to the local stack recipe repository.

        Raises:
            GitNotFoundError: If git is not installed.
        """
        self.cloning_path = cloning_path

        try:
            from git.exc import InvalidGitRepositoryError, NoSuchPathError
            from git.repo.base import Repo
        except ImportError as e:
            logger.error(
                "In order to use the CLI tool to interact with our recipes, "
                "you need to have an installation of Git on your machine."
            )
            raise GitNotFoundError(e)

        try:
            self.repo = Repo(self.cloning_path)
        except (NoSuchPathError, InvalidGitRepositoryError):
            self.repo = None  # type: ignore
            logger.debug(
                f"`Cloning_path`: {self.cloning_path} was empty, "
                "Automatically cloning the recipes."
            )
            self.clone()
            self.checkout_latest_release()

    @property
    def active_version(self) -> Optional[str]:
        """Returns the active version of the repository.

        In case a release branch is checked out, this property returns
        that version as a string, else `None` is returned.

        Returns:
            The active version of the repository.
        """
        for branch in self.repo.heads:
            if (
                branch.name.startswith("release/")
                and branch.commit == self.repo.head.commit
            ):
                return branch.name[len("release/") :]

        return None

    @property
    def latest_release_branch(self) -> str:
        """Returns the name of the latest release branch.

        Returns:
            The name of the latest release branch.
        """
        from packaging.version import Version, parse

        tags = sorted(
            self.repo.tags,
            key=lambda t: t.commit.committed_datetime,
        )

        if not tags:
            return "main"

        latest_tag = parse(tags[-1].name)
        if type(latest_tag) is not Version:
            return "main"

        latest_release_version: str = tags[-1].name
        return f"release/{latest_release_version}"

    @property
    def is_cloned(self) -> bool:
        """Returns whether we have already cloned the repository.

        Returns:
            Whether we have already cloned the repository.
        """
        return self.cloning_path.exists()

    def clone(self) -> None:
        """Clones repo to `cloning_path`.

        If you break off the operation with a `KeyBoardInterrupt` before the
        cloning is completed, this method will delete whatever was partially
        downloaded from your system.
        """
        self.cloning_path.mkdir(parents=True, exist_ok=False)
        try:
            from git.repo.base import Repo

            logger.info(f"Downloading recipes to {self.cloning_path}")
            self.repo = Repo.clone_from(
                STACK_RECIPES_GITHUB_REPO,
                self.cloning_path,
                branch="main",
            )
        except KeyboardInterrupt:
            self.delete()
            logger.error("Canceled download of recipes.. Rolled back.")

    def delete(self) -> None:
        """Delete `cloning_path` if it exists.

        Raises:
            AssertionError: If `cloning_path` does not exist.
        """
        if self.cloning_path.exists():
            shutil.rmtree(self.cloning_path)
        else:
            raise AssertionError(
                f"Cannot delete the stack recipes repository from "
                f"{self.cloning_path} as it does not exist."
            )

    def checkout(self, branch: str) -> None:
        """Checks out a specific branch or tag of the repository.

        Args:
            branch: The name of the branch or tag to check out.
        """
        logger.info(f"Checking out branch: {branch}")
        self.repo.git.checkout(branch)

    def checkout_latest_release(self) -> None:
        """Checks out the latest release of the repository."""
        self.checkout(branch=self.latest_release_branch)


class GitStackRecipesHandler(object):
    """Class for the `GitStackRecipesHandler` that interfaces with the CLI."""

    def __init__(self) -> None:
        """Create a new GitStackRecipesHandler instance."""
        self.repo_dir = io_utils.get_global_config_directory()
        self.stack_recipes_dir = Path(
            os.path.join(self.repo_dir, STACK_RECIPES_REPO_DIR)
        )
        self.stack_recipe_repo = StackRecipeRepo(self.stack_recipes_dir)

    @property
    def stack_recipes(self) -> List[StackRecipe]:
        """Property that contains a list of stack recipes.

        Returns:
            A list of stack recipes.
        """
        return [
            StackRecipe(name, Path(os.path.join(self.stack_recipes_dir, name)))
            for name in sorted(os.listdir(self.stack_recipes_dir))
            if (
                not name.startswith(".")
                and not name.startswith("__")
                and not name == "LICENSE"
                and not name.endswith(".md")
                and not name.endswith(".sh")
                and not name == "modules"
            )
        ]

    def is_stack_recipe(self, stack_recipe_name: Optional[str] = None) -> bool:
        """Checks if the given stack_recipe_name corresponds to a stack_recipe.

        Args:
            stack_recipe_name: The name of the stack_recipe to check.

        Returns:
            Whether the supplied stack_recipe_name corresponds to a
            stack recipe.
        """
        stack_recipe_dict = {
            recipe.name: recipe for recipe in self.stack_recipes
        }
        if stack_recipe_name:
            if stack_recipe_name in stack_recipe_dict.keys():
                return True

        return False

    def get_stack_recipes(
        self, stack_recipe_name: Optional[str] = None
    ) -> List[StackRecipe]:
        """Method that allows you to get a stack recipe by name.

        If no stack recipe is supplied,  all stack recipes are returned.

        Args:
            stack_recipe_name: Name of an stack recipe.

        Returns:
            A list of stack recipes.

        Raises:
            KeyError: If the supplied stack_recipe_name is not found.
        """
        stack_recipe_dict = {
            recipe.name: recipe
            for recipe in self.stack_recipes
            if recipe.name not in EXCLUDED_RECIPE_DIRS
        }
        if stack_recipe_name:
            if stack_recipe_name in stack_recipe_dict.keys():
                return [stack_recipe_dict[stack_recipe_name]]
            else:
                raise KeyError(
                    f"Stack recipe {stack_recipe_name} does not exist! "
                    f"Available Stack Recipes: {list(stack_recipe_dict)}"
                    "If you want to deploy a custom stack recipe available "
                    "locally, please call deploy with the `--skip-pull` flag "
                    "and specify the path to the stack recipe directory with "
                    "the `--path` or `-p` flag."
                )
        else:
            return self.stack_recipes

    def pull(
        self,
        branch: str = "develop",
        force: bool = False,
    ) -> None:
        """Pulls the stack recipes from the main git stack recipes repository.

        Args:
            branch: The name of the branch to pull from.
            force: Whether to force the pull.
        """
        from git.exc import GitCommandError

        if not self.stack_recipe_repo.is_cloned:
            self.stack_recipe_repo.clone()
        elif force:
            self.stack_recipe_repo.delete()
            self.stack_recipe_repo.clone()

        try:
            self.stack_recipe_repo.checkout(branch=branch)
        except GitCommandError:
            logger.warning(
                f"The specified branch {branch} not found in "
                "repo, falling back to the latest release."
            )
            self.stack_recipe_repo.checkout_latest_release()

    def pull_latest_stack_recipes(self) -> None:
        """Pulls the latest stack recipes from the stack recipes repository."""
        self.pull(
            branch=self.stack_recipe_repo.latest_release_branch, force=True
        )

    def copy_stack_recipe(
        self, stack_recipe: StackRecipe, destination_dir: str
    ) -> None:
        """Copies a stack recipe to the destination_dir.

        Args:
            stack_recipe: The stack recipe to copy.
            destination_dir: The destination directory to copy the recipe to.
        """
        io_utils.create_dir_if_not_exists(destination_dir)
        io_utils.copy_dir(
            str(stack_recipe.path_in_repo),
            destination_dir,
            overwrite=True,
        )

    @staticmethod
    def clean_current_stack_recipes() -> None:
        """Deletes the stack recipes directory from your working directory."""
        stack_recipes_directory = os.path.join(
            os.getcwd(), "zenml_stack_recipes"
        )
        shutil.rmtree(stack_recipes_directory)

    def get_active_version(self) -> Optional[str]:
        """Returns the active version of the mlstacks repository.

        Returns:
            The active version of the repository.
        """
        self.stack_recipe_repo.checkout_latest_release()
        return self.stack_recipe_repo.active_version


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
