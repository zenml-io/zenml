#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.

#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:

#       https://www.apache.org/licenses/LICENSE-2.0

#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Functionality to handle downloading ZenML stacks via the CLI."""

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, List, Optional, cast

import click
from packaging.version import Version, parse
from rich.markdown import Markdown
from rich.text import Text

import zenml
from zenml.cli import utils as cli_utils
from zenml.cli.cli import TagGroup
from zenml.cli.stack import import_stack, stack
from zenml.console import console
from zenml.exceptions import GitNotFoundError
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.utils import io_utils
from zenml.utils.analytics_utils import AnalyticsEvent, track_event

logger = get_logger(__name__)

EXCLUDED_RECIPE_DIRS = [""]
STACK_RECIPES_GITHUB_REPO = "https://github.com/zenml-io/mlops-stacks.git"
STACK_RECIPES_REPO_DIR = "zenml_stack_recipes"
VARIABLES_FILE = "values.tfvars.json"
ALPHA_MESSAGE = (
    "The stack recipes CLI is in alpha and actively being developed. "
    "Please avoid running mission-critical workloads on resources deployed "
    "through these commands. If you encounter any problems, create an issue "
    f"on the repository {STACK_RECIPES_GITHUB_REPO} and we'll help you out!"
)
HELP_MESSAGE = "Commands for using the stack recipes."

try:
    # Make sure all stack recipe dependencies are installed
    import python_terraform  # type: ignore

    terraform_installed = True
except ImportError:
    # Unable to import the python_terraform dependencies. Include a help message in
    # the `zenml stack recipe` CLI group and don't add any subcommands that would
    # just fail.
    terraform_installed = False

    HELP_MESSAGE += (
        "\n\n**Note**: The stack recipe commands seem to be unavailable on "
        "your machine. This is probably because ZenML was installed without "
        "the optional terraform dependencies. To install the missing dependencies: \n\n"
        f'`pip install "zenml[stacks]=={zenml.__version__}"`.'
    )


class Terraform:
    """Class to represent terraform applications."""

    def __init__(self, path: str) -> None:
        """Creates a client that can be used to call terraform commands.

        Args:
            path: the path to the stack recipe.
        """
        self.tf = python_terraform.Terraform(working_dir=str(path))

    def check_installation(self) -> None:
        """Checks if terraform is installed on the host system.

        Raises:
            RuntimeError: if terraform is not installed.
        """
        if not self._is_installed():
            raise RuntimeError(
                "Terraform is required for stack recipes to run and was not "
                "found installed on your machine. Please visit "
                "https://learn.hashicorp.com/tutorials/terraform/install-cli "
                "to install it."
            )

    def _is_installed(self) -> bool:
        """Checks if terraform is installed on the host system.

        Returns:
            True if terraform is installed, false otherwise.
        """
        # check terraform version to verify installation.
        ret_code, _, _ = self.tf.cmd("-version")
        return bool(ret_code == 0)

    def apply(self) -> str:
        """Function to call terraform init and terraform apply.

        The init call is not repeated if any successful execution has
        happened already, to save time.

        Returns:
            The path to the stack YAML configuration file as a string.

        Raises:
            RuntimeError: if terraform init fails.
        """
        # this directory gets created after a successful init
        previous_run_dir = os.path.join(self.tf.working_dir, ".ignoreme")
        if fileio.exists(previous_run_dir):
            logger.info(
                "Terraform already initialized, "
                "terraform init will not be executed."
            )
        else:
            ret_code, _, _ = self.tf.init(capture_output=False)
            if ret_code != 0:
                raise RuntimeError("The command 'terraform init' failed.")
            fileio.mkdir(previous_run_dir)

        # get variables from the recipe as a python dictionary
        vars = self._get_vars(self.tf.working_dir)

        # once init is successful, call terraform apply
        self.tf.apply(
            var=vars,
            input=False,
            capture_output=False,
            raise_on_error=True,
        )

        # return the path of the stack yaml file
        _, stack_file_path, _ = self.tf.output("stack-yaml-path")
        return str(stack_file_path)

    def _get_vars(self, path: str) -> Any:
        """Get variables as a dictionary from values.tfvars.json.

        Args:
            path: the path to the stack recipe.

        Returns:
            A dictionary of variables to use for the stack recipes
            derived from the tfvars.json file.

        Raises:
            FileNotFoundError: if the values.tfvars.json file is not
                found in the stack recipe.
        """
        import json

        variables_file_path = os.path.join(path, VARIABLES_FILE)
        if not fileio.exists(variables_file_path):
            raise FileNotFoundError(
                "The file values.tfvars.json was not found in the "
                f"recipe's directory at {variables_file_path}. Please "
                "verify if it exists."
            )

        # read values into a dict and return
        with fileio.open(variables_file_path, "r") as f:
            variables = json.load(f)
        return variables

    def set_log_level(self, log_level: str) -> None:
        """Set TF_LOG env var to the log_level provided by the user.

        Args:
            log_level: One of TRACE, DEBUG, INFO, WARN or ERROR to set
                as the log level for terraform CLI.
        """
        os.environ["TF_LOG"] = log_level

    def destroy(self) -> None:
        """Function to call terraform destroy on the given path."""
        self.tf.destroy(
            capture_output=False,
            raise_on_error=True,
            force=python_terraform.IsNotFlagged,
        )


class LocalStackRecipe:
    """Class to encapsulate the local stack that can be run from the CLI."""

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
        except NoSuchPathError or InvalidGitRepositoryError:
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
            branch_name = cast(str, branch.name)
            if (
                branch_name.startswith("release/")
                and branch.commit == self.repo.head.commit
            ):
                return branch_name[len("release/") :]

        return None

    @property
    def latest_release_branch(self) -> str:
        """Returns the name of the latest release branch.

        Returns:
            The name of the latest release branch.
        """
        tags = sorted(
            self.repo.tags,
            key=lambda t: t.commit.committed_datetime,  # type: ignore
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
                STACK_RECIPES_GITHUB_REPO, self.cloning_path, branch="main"
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
            )
        ]

    def is_stack_recipe(self, stack_recipe_name: Optional[str] = None) -> bool:
        """Checks if the supplied stack_recipe_name corresponds to a stack_recipe.

        Args:
            stack_recipe_name: The name of the stack_recipe to check.

        Returns:
            Whether the supplied stack_recipe_name corresponds to an stack_recipe.
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
        """Method that allows you to get an stack recipe by name.

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
                )
        else:
            return self.stack_recipes

    def pull(
        self,
        branch: str,
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
            cli_utils.warning(
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
        """Copies an stack recipe to the destination_dir.

        Args:
            stack_recipe: The stack recipe to copy.
            destination_dir: The destination directory to copy the recipe to.
        """
        io_utils.create_dir_if_not_exists(destination_dir)
        io_utils.copy_dir(
            str(stack_recipe.path_in_repo), destination_dir, overwrite=True
        )

    def clean_current_stack_recipes(self) -> None:
        """Deletes the ZenML stack recipes directory from your current working directory."""
        stack_recipes_directory = os.path.join(
            os.getcwd(), "zenml_stack_recipes"
        )
        shutil.rmtree(stack_recipes_directory)


pass_git_stack_recipes_handler = click.make_pass_decorator(
    GitStackRecipesHandler, ensure=True
)
pass_tf_client = click.make_pass_decorator(Terraform, ensure=True)


@stack.group("recipe", cls=TagGroup, help=HELP_MESSAGE)
def stack_recipe() -> None:
    """Access all ZenML stack recipes."""


if terraform_installed:  # noqa: C901

    @stack_recipe.command(name="list", help="List the available stack recipes.")
    @pass_git_stack_recipes_handler
    def list_stack_recipes(
        git_stack_recipes_handler: GitStackRecipesHandler,
    ) -> None:
        """List all available stack recipes.

        Args:
            git_stack_recipes_handler: The GitStackRecipesHandler instance.
        """
        cli_utils.warning(ALPHA_MESSAGE)
        stack_recipes = [
            {"stack_recipe_name": stack_recipe.name}
            for stack_recipe in git_stack_recipes_handler.get_stack_recipes()
        ]
        cli_utils.print_table(stack_recipes)

        cli_utils.declare(
            "\n" + "To get the latest list of stack recipes, run: "
        )
        text = Text("zenml stack recipe pull -y", style="markdown.code_block")
        cli_utils.declare(text)

        cli_utils.declare("\n" + "To pull any individual stack recipe, type: ")
        text = Text(
            "zenml stack recipe pull RECIPE_NAME", style="markdown.code_block"
        )
        cli_utils.declare(text)

    @stack_recipe.command(help="Deletes the ZenML stack recipes directory.")
    @click.option(
        "--path",
        "-p",
        type=click.STRING,
        default="zenml_stack_recipes",
        help="Relative path at which you want to clean the stack_recipe(s)",
    )
    @pass_git_stack_recipes_handler
    def clean(
        git_stack_recipes_handler: GitStackRecipesHandler, path: str
    ) -> None:
        """Deletes the ZenML stack recipes directory from your current working directory.

        Args:
            git_stack_recipes_handler: The GitStackRecipesHandler instance.
            path: The path at which you want to clean the stack_recipe(s).
        """
        stack_recipes_directory = os.path.join(os.getcwd(), path)
        if fileio.isdir(stack_recipes_directory) and cli_utils.confirmation(
            "Do you wish to delete the stack recipes directory? \n"
            f"{stack_recipes_directory}"
        ):
            git_stack_recipes_handler.clean_current_stack_recipes()
            cli_utils.declare(
                "Stack recipes directory was deleted from your current working "
                "directory."
            )
        elif not fileio.isdir(stack_recipes_directory):
            logger.error(
                f"Unable to delete the stack recipes directory - "
                f"{stack_recipes_directory} - "
                "as it was not found in your current working directory."
            )

    @stack_recipe.command(help="Find out more about a stack recipe.")
    @pass_git_stack_recipes_handler
    @click.argument("stack_recipe_name")
    def info(
        git_stack_recipes_handler: GitStackRecipesHandler,
        stack_recipe_name: str,
    ) -> None:
        """Find out more about a stack recipe.

        Outputs a pager view of the stack_recipe's README.md file.

        Args:
            git_stack_recipes_handler: The GitStackRecipesHandler instance.
            stack_recipe_name: The name of the stack recipe.
        """
        try:
            stack_recipe_obj = git_stack_recipes_handler.get_stack_recipes(
                stack_recipe_name
            )[0]
        except KeyError as e:
            cli_utils.error(str(e))

        else:
            md = Markdown(stack_recipe_obj.readme_content)
            with console.pager(styles=True):
                console.print(md)

    @stack_recipe.command(
        help="Pull stack recipes straight into your current working directory."
    )
    @pass_git_stack_recipes_handler
    @click.argument("stack_recipe_name", required=False, default=None)
    @click.option(
        "--yes",
        "-y",
        "force",
        is_flag=True,
        help="Force the redownload of the stack_recipes folder to the ZenML config "
        "folder.",
    )
    @click.option(
        "--path",
        "-p",
        type=click.STRING,
        default="zenml_stack_recipes",
        help="Relative path at which you want to install the stack recipe(s)",
    )
    def pull(
        git_stack_recipes_handler: GitStackRecipesHandler,
        stack_recipe_name: str,
        force: bool,
        path: str,
    ) -> None:
        """Pull stack_recipes straight into your current working directory.

        Add the flag --yes or -y to redownload all the stack_recipes afresh.
        Use the flag --version or -v and the version number to specify
        which version of ZenML you wish to use for the stack_recipes.

        Args:
            git_stack_recipes_handler: The GitStackRecipesHandler instance.
            stack_recipe_name: The name of the stack_recipe.
            force: Force the redownload of the stack_recipes folder to the ZenML config
                folder.
            path: The path at which you want to install the stack_recipe(s).
        """
        cli_utils.warning(ALPHA_MESSAGE)
        git_stack_recipes_handler.pull(branch="main", force=force)

        stack_recipes_dir = os.path.join(os.getcwd(), path)
        io_utils.create_dir_if_not_exists(stack_recipes_dir)
        try:
            stack_recipes = git_stack_recipes_handler.get_stack_recipes(
                stack_recipe_name
            )
        except KeyError as e:
            cli_utils.error(str(e))

        else:
            for stack_recipe in stack_recipes:
                destination_dir = os.path.join(
                    os.getcwd(), path, stack_recipe.name
                )
                if LocalStackRecipe(
                    name=stack_recipe.name, path=Path(destination_dir)
                ).is_present():
                    if force or cli_utils.confirmation(
                        f"Stack recipe {stack_recipe.name} is already pulled. "
                        "Do you wish to overwrite the directory at "
                        f"{destination_dir}?"
                    ):
                        fileio.rmtree(destination_dir)
                    else:
                        cli_utils.warning(
                            f"Stack recipe {stack_recipe.name} not overwritten."
                        )
                        continue

                cli_utils.declare(
                    f"Pulling stack recipe {stack_recipe.name}..."
                )

                io_utils.create_dir_if_not_exists(destination_dir)
                git_stack_recipes_handler.copy_stack_recipe(
                    stack_recipe, destination_dir
                )
                cli_utils.declare(
                    f"Stack recipe pulled in directory: {destination_dir}"
                )
                cli_utils.declare(
                    "\n Please edit the configuration values as you see fit, "
                    f"in the file: {os.path.join(destination_dir, 'locals.tf')} "
                    "before you run the deploy command."
                )
                track_event(
                    AnalyticsEvent.PULL_STACK_RECIPE,
                    {"stack_recipe_name": stack_recipe.name},
                )

    @stack_recipe.command(
        help="Run the stack_recipe that you previously pulled with "
        "`zenml stack recipe pull`"
    )
    @click.argument("stack_recipe_name", required=True)
    @click.option(
        "--path",
        "-p",
        type=click.STRING,
        default="zenml_stack_recipes",
        help="Relative path at which you want to install the stack_recipe(s)",
    )
    @click.option(
        "--force",
        "-f",
        "force",
        is_flag=True,
        help="Force the run of the stack_recipe. This deletes the .zen folder from the "
        "stack_recipe folder and force installs all necessary integration "
        "requirements.",
    )
    @click.option(
        "--stack-name",
        "-n",
        type=click.STRING,
        required=False,
        help="Set a name for the ZenML stack that will be imported from the YAML "
        "configuration file which gets generated after deploying the stack recipe. "
        "Defaults to the name of the stack recipe being deployed.",
    )
    @click.option(
        "--import",
        "import_stack_flag",
        is_flag=True,
        help="Don't import the stack automatically after the recipe is deployed. The "
        "stack configuration file is still generated and can be imported manually.",
    )
    @click.option(
        "--log-level",
        type=click.Choice(
            ["TRACE", "DEBUG", "INFO", "WARN", "ERROR"], case_sensitive=False
        ),
        help="Choose one of TRACE, DEBUG, INFO, WARN or ERROR (case insensitive) as "
        "log level for the deploy operation.",
        default="ERROR",
    )
    @pass_git_stack_recipes_handler
    @click.pass_context
    def deploy(
        ctx: click.Context,
        git_stack_recipes_handler: GitStackRecipesHandler,
        stack_recipe_name: str,
        path: str,
        force: bool,
        import_stack_flag: bool,
        log_level: str,
        stack_name: Optional[str],
    ) -> None:
        """Run the stack_recipe at the specified relative path.

        `zenml stack_recipe pull <STACK_RECIPE_NAME>` has to be called with the same relative
        path before the deploy command.

        Args:
            ctx: The click context.
            git_stack_recipes_handler: The GitStackRecipesHandler instance.
            stack_recipe_name: The name of the stack_recipe.
            path: The path at which you want to install the stack_recipe(s).
            force: Force the run of the stack_recipe.
            stack_name: A name for the ZenML stack that gets imported as a result
                of the recipe deployment.
            import_stack_flag: Import the stack automatically after the recipe is
                deployed. The stack configuration file is always generated and
                can be imported manually otherwise.
            log_level: Choose one of TRACE, DEBUG, INFO, WARN or ERROR (case insensitive)
                as log level for the deploy operation.
        """
        cli_utils.warning(ALPHA_MESSAGE)
        stack_recipes_dir = Path(os.getcwd()) / path

        if sys.platform == "win32":
            logger.info(
                "If you are running stack_recipes on Windows, make sure that you have "
                "an associated application with executing .sh files. If you don't "
                "have any and you see a pop-up during 'zenml stack_recipe run', we "
                "suggest to use the Git BASH: https://gitforwindows.org/"
            )

        try:
            _ = git_stack_recipes_handler.get_stack_recipes(stack_recipe_name)[
                0
            ]
        except KeyError as e:
            cli_utils.error(str(e))
        else:
            stack_recipe_dir = stack_recipes_dir / stack_recipe_name
            local_stack_recipe = LocalStackRecipe(
                stack_recipe_dir, stack_recipe_name
            )

            if not local_stack_recipe.is_present():
                ctx.invoke(
                    pull,
                    stack_recipe_name=stack_recipe_name,
                    path=path,
                    force=force,
                )

            try:
                # check if terraform is installed
                tf_client = Terraform(str(local_stack_recipe.path))
                try:
                    tf_client.check_installation()
                except RuntimeError as e:
                    cli_utils.error(str(e))

                # set terraform log level
                tf_client.set_log_level(log_level=log_level)

                logger.info(
                    "The following values are selected for the configuration "
                    "of your cloud resources. You can change it by modifying "
                    "the contents of the locals.tf file here: "
                    f"{os.path.join(local_stack_recipe.path, 'locals.tf')}\n"
                )

                with console.pager(styles=False):
                    console.print(local_stack_recipe.locals_content)

                if cli_utils.confirmation(
                    f"\nDo you wish to deploy the {stack_recipe_name} recipe "
                    "with the above configuration? Please make sure that "
                    "resources with the same values as above don't already "
                    "exist on your cloud account."
                ):

                    # Telemetry
                    track_event(
                        AnalyticsEvent.RUN_STACK_RECIPE,
                        {"stack_recipe_name": stack_recipe_name},
                    )
                    # use the terraform client to apply recipe
                    stack_yaml_file = os.path.join(
                        local_stack_recipe.path,
                        tf_client.apply(),
                    )

                    logger.info(
                        "\nA stack configuration YAML file has been generated as "
                        f"part of the deployment of the {stack_recipe_name} recipe. "
                        f"Find it at {stack_yaml_file}."
                    )

                    if import_stack_flag:
                        logger.info(
                            "\nThe flag `--no-import` is not set. Proceeding "
                            "to import a new ZenML stack from the created resources."
                        )
                        import_stack_name = (
                            stack_name if stack_name else stack_recipe_name
                        )
                        cli_utils.declare(
                            f"Importing a new stack with the name {import_stack_name}."
                        )

                        # import deployed resources as ZenML stack
                        ctx.invoke(
                            import_stack,
                            stack_name=stack_name,
                            filename=stack_yaml_file,
                            ignore_version_mismatch=True,
                        )

                        cli_utils.declare(
                            "Please consider creating any secrets that your stack "
                            "components like the metadata store might need. "
                            "You can inspect the fields of a stack component by "
                            "running a describe command on them."
                        )
                        cli_utils.declare(
                            "\n Run 'terraform output' in the recipe's directory at "
                            f"{local_stack_recipe.path} to get a list of outputs. To now "
                            "retrieve sensitive outputs, for example, the metadata-db-password "
                            "use the command 'terraform output metadata-db-password' to get the "
                            "value in the command-line."
                        )

            except RuntimeError as e:
                cli_utils.error(
                    f"Error running recipe {stack_recipe_name}: {str(e)} "
                    "\nPlease look at the error message to figure out why the "
                    "command failed. If the error is due some wrong configuration, "
                    "please consider checking the locals.tf file to verify if the "
                    "inputs are correct. Most commonly, the command can fail due "
                    "to a timeout error. In that case, please"
                    f"run zenml stack recipe deploy {stack_recipe_name} again"
                )
            except python_terraform.TerraformCommandError as e:
                cli_utils.error(
                    f"Error running recipe {stack_recipe_name}: {str(e.err)} "
                    "\nPlease look at the error message to figure out why the "
                    "command failed. If the error is due some wrong configuration, "
                    "please consider checking the locals.tf file to verify if the "
                    "inputs are correct. Most commonly, the command can fail due "
                    "to a timeout error. In that case, please"
                    f"run zenml stack recipe deploy {stack_recipe_name} again"
                )

    @stack_recipe.command(
        help="Destroy the stack components created previously with "
        "`zenml stack recipe deploy <name>`"
    )
    @click.argument("stack_recipe_name", required=True)
    @click.option(
        "--path",
        "-p",
        type=click.STRING,
        default="zenml_stack_recipes",
        help="Relative path at which you want to install the stack_recipe(s)",
    )
    @click.option(
        "--log-level",
        type=click.Choice(
            ["TRACE", "DEBUG", "INFO", "WARN", "ERROR"], case_sensitive=False
        ),
        help="Choose one of TRACE, DEBUG, INFO, WARN or ERROR (case insensitive) as "
        "log level for the destroy operation.",
        default="ERROR",
    )
    @pass_git_stack_recipes_handler
    @click.pass_context
    def destroy(
        ctx: click.Context,
        git_stack_recipes_handler: GitStackRecipesHandler,
        stack_recipe_name: str,
        path: str,
        log_level: str,
    ) -> None:
        """Destroy all resources from the stack_recipe at the specified relative path.

        `zenml stack_recipe deploy stack_recipe_name` has to be called with the same relative
        path before the destroy command.

        Args:
            ctx: The click context.
            git_stack_recipes_handler: The GitStackRecipesHandler instance.
            stack_recipe_name: The name of the stack_recipe.
            path: The path at which you want to install the stack_recipe(s).
            log_level: Choose one of TRACE, DEBUG, INFO, WARN or ERROR (case insensitive)
                as log level for the deploy operation.

        Raises:
            ModuleNotFoundError: If the recipe is found at the given path.
        """
        cli_utils.warning(ALPHA_MESSAGE)

        stack_recipes_dir = Path(os.getcwd()) / path

        if sys.platform == "win32":
            logger.info(
                "If you are running stack_recipes on Windows, make sure that you have "
                "an associated application with executing .sh files. If you don't "
                "have any and you see a pop-up during 'zenml stack_recipe run', we "
                "suggest to use the Git BASH: https://gitforwindows.org/"
            )

        try:
            _ = git_stack_recipes_handler.get_stack_recipes(stack_recipe_name)[
                0
            ]
        except KeyError as e:
            cli_utils.error(str(e))
        else:
            stack_recipe_dir = stack_recipes_dir / stack_recipe_name
            local_stack_recipe = LocalStackRecipe(
                stack_recipe_dir, stack_recipe_name
            )

            if not local_stack_recipe.is_present():
                raise ModuleNotFoundError(
                    f"The recipe {stack_recipe_name} "
                    "has not been pulled at the specified path. "
                    f"Run `zenml stack recipe pull {stack_recipe_name}` "
                    f"followed by `zenml stack recipe deploy {stack_recipe_name}` first."
                )

            try:
                # check if terraform is installed
                tf_client = Terraform(str(local_stack_recipe.path))
                try:
                    tf_client.check_installation()
                except RuntimeError as e:
                    cli_utils.error(str(e))

                # set terraform log level
                tf_client.set_log_level(log_level=log_level)

                # Telemetry
                track_event(
                    AnalyticsEvent.DESTROY_STACK_RECIPE,
                    {"stack_recipe_name": stack_recipe_name},
                )
                # use the terraform client to call destroy on the recipe
                tf_client.destroy()

                cli_utils.declare(
                    "\n" + "Your active stack might now be invalid. Please run:"
                )
                text = Text("zenml stack describe", style="markdown.code_block")
                cli_utils.declare(text)
                cli_utils.declare(
                    "\n" + "to investigate and switch to a new stack if needed."
                )

            except python_terraform.TerraformCommandError as e:
                force_message = ""
                if stack_recipe_name == "aws_minimal":
                    force_message = (
                        "If there are Kubernetes resources that aren't"
                    )
                    "getting deleted, run 'kubectl delete node -all' to delete the "
                    "nodes and consequently all Kubernetes resources. Run the destroy "
                    "again after that, to remove any other remaining resources."
                cli_utils.error(
                    f"Error destroying recipe {stack_recipe_name}: {str(e.err)}"
                    "\nMost commonly, the error occurs if there's some resource "
                    "that can't be deleted instantly, for example, MySQL stores "
                    "with backups. In such cases, please try again after "
                    "around 30 minutes. If the issue persists, kindly raise an "
                    f"issue at {STACK_RECIPES_GITHUB_REPO}. \n{force_message}"
                )
            except subprocess.CalledProcessError as e:
                cli_utils.warning(
                    f"Error destroying recipe {stack_recipe_name}: {str(e)}"
                    "\nThe kubernetes cluster couldn't be removed due to the error "
                    "above. Please verify if the cluster has already been deleted by "
                    "running kubectl get nodes to check if there's any active nodes."
                    "Ignore this warning if there are no active nodes."
                )
