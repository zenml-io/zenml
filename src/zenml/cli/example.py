#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.

#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:

#       https://www.apache.org/licenses/LICENSE-2.0

#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, cast

import click
from packaging.version import Version, parse
from rich.markdown import Markdown
from rich.text import Text

import zenml.io.utils
from zenml import __version__ as zenml_version_installed
from zenml.cli.cli import TagGroup, cli
from zenml.cli.utils import confirmation, declare, error, print_table, warning
from zenml.console import console
from zenml.constants import GIT_REPO_URL
from zenml.exceptions import GitNotFoundError
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.utils.analytics_utils import AnalyticsEvent, track_event

logger = get_logger(__name__)

EXCLUDED_EXAMPLE_DIRS = ["add_your_own"]
EXAMPLES_GITHUB_REPO = "zenml_examples"
EXAMPLES_RUN_SCRIPT = "run_example.sh"
SHELL_EXECUTABLE = "SHELL_EXECUTABLE"


class LocalExample:
    """Class to encapsulate all properties and methods of the local example
    that can be run from the CLI"""

    def __init__(self, path: Path, name: str) -> None:
        """Create a new LocalExample instance.

        Args:
            name: The name of the example, specifically the name of the folder
                  on git
            path: Path at which the example is installed
        """
        self.name = name
        self.path = path

    @property
    def python_files_in_dir(self) -> List[str]:
        """List of all python files in the drectl in local example directory
        the __init__.py file is excluded from this list"""
        py_in_dir = zenml.io.utils.find_files(str(self.path), "*.py")
        py_files = []
        for file in py_in_dir:
            # Make sure only files directly in dir are considered, not files
            # in sub dirs
            if self.path == Path(file).parent:
                if Path(file).name != "__init__.py":
                    py_files.append(file)

        return py_files

    @property
    def has_single_python_file(self) -> bool:
        """Boolean that states if only one python file is present"""
        return len(self.python_files_in_dir) == 1

    @property
    def has_any_python_file(self) -> bool:
        """Boolean that states if any python file is present"""
        return len(self.python_files_in_dir) > 0

    @property
    def run_dot_py_file(self) -> Optional[str]:
        """Returns the path to the run.py file in case one exists"""
        for file in self.python_files_in_dir:
            # Make sure only files directly in dir are considered, not files
            # in sub dirs
            if self.path == Path(file).parent:
                if Path(file).name == "run.py":
                    return file
        return None

    @property
    def needs_manual_user_setup(self) -> bool:
        """Checks if a setup.sh file exist in the example dir, signifying the
        possibility to run the example without any user input. Examples with no
        setup.sh file need the user to setup infrastructure and/or connect
        to tools/service providers

        Returns:
            True if no setup.sh file in self.path, False else
        """
        return not zenml.io.fileio.exists(
            os.path.join(str(self.path), "setup.sh")
        )

    @property
    def executable_python_example(self) -> str:
        """Return the Python file for the example"""

        if self.needs_manual_user_setup:
            raise NotImplementedError(
                "This example currently does not support being run from the "
                "CLI as user specific setup is required. Consult the README.md "
                "of the example to find out more."
            )
        elif self.has_single_python_file:
            return self.python_files_in_dir[0]
        elif self.run_dot_py_file:
            return self.run_dot_py_file
        elif self.has_any_python_file:
            logger.warning(
                "This example has multiple executable python files. "
                "The last one in alphanumerical order is taken."
            )
            return sorted(self.python_files_in_dir)[-1]
        else:
            raise RuntimeError(
                "No pipeline runner script found in example. "
                f"Files found: {self.python_files_in_dir}"
            )

    def is_present(self) -> bool:
        """Checks if the example exists at the given path."""
        return fileio.exists(str(self.path)) and fileio.isdir(str(self.path))

    def run_example(
        self,
        example_runner: List[str],
        force: bool,
        prevent_stack_setup: bool = False,
    ) -> None:
        """Run the local example using the bash script at the supplied
        location

        Args:
            example_runner: Sequence of locations of executable file(s)
                            to run the example
            force: Whether to force the install
            prevent_stack_setup: Prevents the example from setting up a custom
                stack.
        """
        if all(map(fileio.exists, example_runner)):
            call = (
                example_runner
                + ["--executable", self.executable_python_example]
                + ["-y"] * force
                + ["--no-stack-setup"] * prevent_stack_setup
            )
            try:
                # TODO [ENG-271]: Catch errors that might be thrown
                #  in subprocess
                subprocess.check_call(
                    call,
                    cwd=str(self.path),
                    shell=click._compat.WIN,
                    env=os.environ.copy(),
                )
            except RuntimeError:
                raise NotImplementedError(
                    f"Currently the example {self.name} "
                    "has no implementation for the "
                    "run method"
                )
            except subprocess.CalledProcessError as e:
                if e.returncode == 38:
                    raise NotImplementedError(
                        f"Currently the example {self.name} "
                        "has no implementation for the "
                        "run method"
                    )
                raise
        else:
            raise FileNotFoundError(
                "Bash File(s) to run Examples not found at" f"{example_runner}"
            )

        # Telemetry
        track_event(AnalyticsEvent.RUN_EXAMPLE, {"example_name": self.name})


class Example:
    """Class for all example objects."""

    def __init__(self, name: str, path_in_repo: Path) -> None:
        """Create a new Example instance.

        Args:
            name: The name of the example, specifically the name of the folder
                  on git
            path_in_repo: Path to the local example within the global zenml
                  folder.
        """
        self.name = name
        self.path_in_repo = path_in_repo

    @property
    def readme_content(self) -> str:
        """Returns the readme content associated with a particular example."""
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
                    f"Example {self.name} is not one of the available options."
                    f"\n"
                    f"To list all available examples, type: `zenml example "
                    f"list`"
                )


class ExamplesRepo:
    """Class for the examples repository object."""

    def __init__(self, cloning_path: Path) -> None:
        """Create a new ExamplesRepo instance."""
        self.cloning_path = cloning_path

        try:
            from git.exc import InvalidGitRepositoryError, NoSuchPathError
            from git.repo.base import Repo
        except ImportError as e:
            logger.error(
                "In order to use the CLI tool to interact with our examples, "
                "you need to have an installation of Git on your machine."
            )
            raise GitNotFoundError(e)

        try:
            self.repo = Repo(self.cloning_path)
        except NoSuchPathError or InvalidGitRepositoryError:
            self.repo = None  # type: ignore
            logger.debug(
                f"`Cloning_path`: {self.cloning_path} was empty, "
                "Automatically cloning the examples."
            )
            self.clone()
            self.checkout_latest_release()

    @property
    def active_version(self) -> Optional[str]:
        """In case a release branch is checked out, this property returns
        that version, else `None` is returned"""
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
        """Returns the name of the latest release branch."""
        tags = sorted(
            self.repo.tags,
            key=lambda t: t.commit.committed_datetime,  # type: ignore
        )
        latest_tag = parse(tags[-1].name)
        if type(latest_tag) is not Version:
            return "main"

        latest_release_version: str = tags[-1].name
        return f"release/{latest_release_version}"

    @property
    def is_cloned(self) -> bool:
        """Returns whether we have already cloned the examples repository."""
        return self.cloning_path.exists()

    @property
    def examples_dir(self) -> str:
        """Returns the path for the examples directory."""
        return os.path.join(self.cloning_path, "examples")

    @property
    def examples_run_bash_script(self) -> str:
        """Path to the bash script that runs the example."""
        return os.path.join(self.examples_dir, EXAMPLES_RUN_SCRIPT)

    def clone(self) -> None:
        """Clones repo to `cloning_path`.

        If you break off the operation with a `KeyBoardInterrupt` before the
        cloning is completed, this method will delete whatever was partially
        downloaded from your system."""
        self.cloning_path.mkdir(parents=True, exist_ok=False)
        try:
            from git.repo.base import Repo

            logger.info(f"Cloning repo {GIT_REPO_URL} to {self.cloning_path}")
            self.repo = Repo.clone_from(
                GIT_REPO_URL, self.cloning_path, branch="main"
            )
        except KeyboardInterrupt:
            self.delete()
            logger.error("Canceled download of repository.. Rolled back.")

    def delete(self) -> None:
        """Delete `cloning_path` if it exists."""
        if self.cloning_path.exists():
            shutil.rmtree(self.cloning_path)
        else:
            raise AssertionError(
                f"Cannot delete the examples repository from "
                f"{self.cloning_path} as it does not exist."
            )

    def checkout(self, branch: str) -> None:
        """Checks out a specific branch or tag of the examples repository.

        Raises:
            GitCommandError: if branch doesn't exist.
        """
        logger.info(f"Checking out branch: {branch}")
        self.repo.git.checkout(branch)

    def checkout_latest_release(self) -> None:
        """Checks out the latest release of the examples repository."""
        self.checkout(branch=self.latest_release_branch)


class GitExamplesHandler(object):
    """Class for the `GitExamplesHandler` that interfaces with the CLI tool."""

    def __init__(self) -> None:
        """Create a new GitExamplesHandler instance."""
        self.repo_dir = zenml.io.utils.get_global_config_directory()
        self.examples_dir = Path(
            os.path.join(self.repo_dir, EXAMPLES_GITHUB_REPO)
        )
        self.examples_repo = ExamplesRepo(self.examples_dir)

    @property
    def examples(self) -> List[Example]:
        """Property that contains a list of examples."""
        return [
            Example(
                name, Path(os.path.join(self.examples_repo.examples_dir, name))
            )
            for name in sorted(os.listdir(self.examples_repo.examples_dir))
            if (
                not name.startswith(".")
                and not name.startswith("__")
                and not name.startswith("README")
                and not name.endswith(".sh")
            )
        ]

    @property
    def is_matching_versions(self) -> bool:
        """Returns a boolean whether the checked out examples are on the
        same code version as zenml"""
        return zenml_version_installed == str(self.examples_repo.active_version)

    def is_example(self, example_name: Optional[str] = None) -> bool:
        """Checks if the supplied example_name corresponds to an example"""
        example_dict = {e.name: e for e in self.examples}
        if example_name:
            if example_name in example_dict.keys():
                return True

        return False

    def get_examples(self, example_name: Optional[str] = None) -> List[Example]:
        """Method that allows you to get an example by name. If no example is
        supplied,  all examples are returned

        Args:
          example_name: Name of an example.
        """
        example_dict = {
            e.name: e
            for e in self.examples
            if e.name not in EXCLUDED_EXAMPLE_DIRS
        }
        if example_name:
            if example_name in example_dict.keys():
                return [example_dict[example_name]]
            else:
                raise KeyError(
                    f"Example {example_name} does not exist! "
                    f"Available examples: {list(example_dict)}"
                )
        else:
            return self.examples

    def pull(
        self,
        branch: str,
        force: bool = False,
    ) -> None:
        from git.exc import GitCommandError

        """Pulls the examples from the main git examples repository."""
        if not self.examples_repo.is_cloned:
            self.examples_repo.clone()
        elif force:
            self.examples_repo.delete()
            self.examples_repo.clone()

        try:
            self.examples_repo.checkout(branch=branch)
        except GitCommandError:
            warning(
                f"The specified branch {branch} not found in "
                "repo, falling back to the latest release."
            )
            self.examples_repo.checkout_latest_release()

    def pull_latest_examples(self) -> None:
        """Pulls the latest examples from the examples repository."""
        self.pull(branch=self.examples_repo.latest_release_branch, force=True)

    def copy_example(self, example: Example, destination_dir: str) -> None:
        """Copies an example to the destination_dir."""
        zenml.io.utils.create_dir_if_not_exists(destination_dir)
        zenml.io.utils.copy_dir(
            str(example.path_in_repo), destination_dir, overwrite=True
        )

    def clean_current_examples(self) -> None:
        """Deletes the ZenML examples directory from your current working
        directory."""
        examples_directory = os.path.join(os.getcwd(), "zenml_examples")
        shutil.rmtree(examples_directory)


pass_git_examples_handler = click.make_pass_decorator(
    GitExamplesHandler, ensure=True
)


def check_for_version_mismatch(
    git_examples_handler: GitExamplesHandler,
) -> None:
    """Prints a warning if the example version and ZenML version don't match."""
    if git_examples_handler.is_matching_versions:
        return
    else:
        if git_examples_handler.examples_repo.active_version:
            warning(
                "The examples you have installed are installed with Version "
                f"{git_examples_handler.examples_repo.active_version} "
                f"of ZenML. However your code is at {zenml_version_installed} "
                "Consider using `zenml example pull` to download  "
                "examples matching your zenml installation."
            )
        else:
            warning(
                "The examples you have installed are downloaded from a "
                "development branch of ZenML. Full functionality is not "
                "guaranteed. Use `zenml example pull` to "
                "get examples using your zenml version."
            )


@cli.group(cls=TagGroup)
def example() -> None:
    """Access all ZenML examples."""


@example.command(help="List the available examples.")
@pass_git_examples_handler
def list_examples(git_examples_handler: GitExamplesHandler) -> None:
    """List all available examples."""
    check_for_version_mismatch(git_examples_handler)
    examples = [
        {"example_name": example.name}
        for example in git_examples_handler.get_examples()
    ]
    print_table(examples)

    declare("\n" + "To pull the examples, type: ")
    text = Text("zenml example pull EXAMPLE_NAME", style="markdown.code_block")
    declare(text)


@click.option(
    "--path",
    "-p",
    type=click.STRING,
    default="zenml_examples",
    help="Relative path at which you want to clean the example(s)",
)
@example.command(help="Deletes the ZenML examples directory.")
@pass_git_examples_handler
def clean(git_examples_handler: GitExamplesHandler, path: str) -> None:
    """Deletes the ZenML examples directory from your current working
    directory."""
    examples_directory = os.path.join(os.getcwd(), path)
    if (
        fileio.exists(examples_directory)
        and fileio.isdir(examples_directory)
        and confirmation(
            "Do you wish to delete the ZenML examples directory? \n"
            f"{examples_directory}"
        )
    ):
        git_examples_handler.clean_current_examples()
        declare(
            "ZenML examples directory was deleted from your current working "
            "directory."
        )
    elif not fileio.exists(examples_directory) and not fileio.isdir(
        examples_directory
    ):
        logger.error(
            f"Unable to delete the ZenML examples directory - "
            f"{examples_directory} - "
            "as it was not found in your current working directory."
        )


@example.command(help="Find out more about an example.")
@pass_git_examples_handler
@click.argument("example_name")
def info(git_examples_handler: GitExamplesHandler, example_name: str) -> None:
    """Find out more about an example. Outputs a pager view of the example's
    README.md file."""
    check_for_version_mismatch(git_examples_handler)

    try:
        example_obj = git_examples_handler.get_examples(example_name)[0]

    except KeyError as e:
        error(str(e))

    else:
        md = Markdown(example_obj.readme_content)
        with console.pager(styles=True):
            console.print(md)


@example.command(
    help="Pull examples straight into your current working directory."
)
@pass_git_examples_handler
@click.argument("example_name", required=False, default=None)
@click.option(
    "--yes",
    "-y",
    "force",
    is_flag=True,
    help="Force the redownload of the examples folder to the ZenML config "
    "folder.",
)
@click.option(
    "--force",
    "-f",
    "old_force",
    is_flag=True,
    help="DEPRECATED: Force the redownload of the examples folder to the ZenML "
    "config folder. Use `-y/--yes` instead.",
)
@click.option(
    "--version",
    "-v",
    type=click.STRING,
    default=zenml_version_installed,
    help="The version of ZenML to use for the force-redownloaded examples.",
)
@click.option(
    "--branch",
    "-b",
    type=click.STRING,
    default=None,
    hidden=True,
    help="The branch of the ZenML repo to use for the force-redownloaded "
    "examples.",
)
@click.option(
    "--path",
    "-p",
    type=click.STRING,
    default="zenml_examples",
    help="Relative path at which you want to install the example(s)",
)
def pull(
    git_examples_handler: GitExamplesHandler,
    example_name: str,
    force: bool,
    old_force: bool,
    version: str,
    path: str,
    branch: Optional[str],
) -> None:
    """Pull examples straight into your current working directory.
    Add the flag --yes or -y to redownload all the examples afresh.
    Use the flag --version or -v and the version number to specify
    which version of ZenML you wish to use for the examples."""
    if old_force:
        force = old_force
        warning(
            "The `--force` flag will soon be deprecated. Use `--yes` or "
            "`-y` instead."
        )

    branch = branch.strip() if branch else f"release/{version}"
    git_examples_handler.pull(branch=branch, force=force)

    examples_dir = os.path.join(os.getcwd(), path)
    zenml.io.utils.create_dir_if_not_exists(examples_dir)
    try:
        examples = git_examples_handler.get_examples(example_name)

    except KeyError as e:
        error(str(e))

    else:
        for example in examples:
            destination_dir = os.path.join(os.getcwd(), path, example.name)
            if LocalExample(
                name=example.name, path=Path(destination_dir)
            ).is_present():
                if force or confirmation(
                    f"Example {example.name} is already pulled. "
                    "Do you wish to overwrite the directory at "
                    f"{destination_dir}?"
                ):
                    fileio.rmtree(destination_dir)
                else:
                    warning(f"Example {example.name} not overwritten.")
                    continue

            declare(f"Pulling example {example.name}...")

            zenml.io.utils.create_dir_if_not_exists(destination_dir)
            git_examples_handler.copy_example(example, destination_dir)
            declare(f"Example pulled in directory: {destination_dir}")
            track_event(
                AnalyticsEvent.PULL_EXAMPLE, {"example_name": example.name}
            )


@example.command(
    help="Run the example that you previously installed with "
    "`zenml example pull`"
)
@click.argument("example_name", required=True)
@click.option(
    "--path",
    "-p",
    type=click.STRING,
    default="zenml_examples",
    help="Relative path at which you want to install the example(s)",
)
@click.option(
    "--yes",
    "-y",
    "force",
    is_flag=True,
    help="Force the run of the example. This deletes the .zen folder from the "
    "example folder and force installs all necessary integration "
    "requirements.",
)
@click.option(
    "--force",
    "-f",
    "old_force",
    is_flag=True,
    help="DEPRECATED: Force the run of the example. This deletes the .zen "
    "folder from the example folder and force installs all necessary "
    "integration requirements. Use `-y/--yes` instead.",
)
@click.option(
    "--shell-executable",
    "-x",
    type=click.Path(exists=True),
    required=False,
    envvar=SHELL_EXECUTABLE,
    help="Manually specify the path to the executable that runs .sh files. "
    "Can be helpful for compatibility with Windows or minimal linux "
    "distros without bash.",
)
@pass_git_examples_handler
@click.pass_context
def run(
    ctx: click.Context,
    git_examples_handler: GitExamplesHandler,
    example_name: str,
    path: str,
    force: bool,
    old_force: bool,
    shell_executable: Optional[str],
) -> None:
    """Run the example at the specified relative path.
    `zenml example pull EXAMPLE_NAME` has to be called with the same relative
    path before the run command.
    """
    if old_force:
        force = old_force
        warning(
            "The `--force` flag will soon be deprecated. Use `--yes` or "
            "`-y` instead."
        )
    check_for_version_mismatch(git_examples_handler)

    # TODO [ENG-272]: - create a post_run function inside individual setup.sh
    #  to inform user how to clean up
    examples_dir = Path(os.getcwd()) / path

    if sys.platform == "win32":
        logger.info(
            "If you are running examples on Windows, make sure that you have "
            "an associated application with executing .sh files. If you don't "
            "have any and you see a pop-up during 'zenml example run', we "
            "suggest to use the Git BASH: https://gitforwindows.org/"
        )

    try:
        _ = git_examples_handler.get_examples(example_name)[0]
    except KeyError as e:
        error(str(e))
    else:
        example_dir = examples_dir / example_name
        local_example = LocalExample(example_dir, example_name)

        if not local_example.is_present():
            ctx.invoke(pull, example_name=example_name, path=path, force=force)

        example_runner = (
            [] if shell_executable is None else [shell_executable]
        ) + [git_examples_handler.examples_repo.examples_run_bash_script]
        try:
            local_example.run_example(
                example_runner=example_runner, force=force
            )
        except NotImplementedError as e:
            error(str(e))
