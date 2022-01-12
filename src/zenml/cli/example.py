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
from pathlib import Path
from typing import List, Optional

import click
from git.exc import GitCommandError, InvalidGitRepositoryError, NoSuchPathError
from git.repo.base import Repo
from packaging.version import Version, parse

import zenml.io.utils
from zenml import __version__ as zenml_version_installed
from zenml.cli.cli import cli
from zenml.cli.utils import (
    confirmation,
    declare,
    error,
    pretty_print,
    title,
    warning,
)
from zenml.constants import GIT_REPO_URL
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.utils.analytics_utils import RUN_EXAMPLE, track_event

logger = get_logger(__name__)

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
        py_in_dir = fileio.find_files(str(self.path), "*.py")
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
    def executable_python_example(self) -> str:
        """Return the python file for the example"""
        if self.has_single_python_file:
            return self.python_files_in_dir[0]
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
        """Checks if the example is installed at the given path."""
        return fileio.file_exists(str(self.path)) and fileio.is_dir(
            str(self.path)
        )

    def run_example(self, example_runner: List[str], force: bool) -> None:
        """Run the local example using the bash script at the supplied
        location

        Args:
            example_runner: Sequence of locations of executable file(s)
                            to run the example
            force: Whether to force the install
        """
        if all(map(fileio.file_exists, example_runner)):
            call = (
                example_runner
                + ["--executable", self.executable_python_example]
                + ["-f"] * force
            )
            try:
                # TODO [ENG-271]: Catch errors that might be thrown
                #  in subprocess
                subprocess.check_call(
                    call, cwd=str(self.path), shell=click._compat.WIN
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
        else:
            raise FileNotFoundError(
                "Bash File(s) to run Examples not found at" f"{example_runner}"
            )

        # Telemetry
        track_event(RUN_EXAMPLE, {"name": self.name})


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
            if fileio.file_exists(str(self.path_in_repo)) and fileio.is_dir(
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
            self.repo = Repo(self.cloning_path)
        except NoSuchPathError or InvalidGitRepositoryError:
            self.repo = None  # type: ignore
            logger.debug(
                f"`Cloning_path`: {self.cloning_path} was empty, "
                "Automatically cloning the examples."
            )
            self.clone()
            self.checkout(branch=self.latest_release)

    @property
    def active_version(self) -> Optional[str]:
        """In case a tagged version is checked out, this property returns
        that version, else None is returned"""
        return next(
            (
                tag
                for tag in self.repo.tags
                if tag.commit == self.repo.head.commit
            ),
            None,
        )

    @property
    def latest_release(self) -> str:
        """Returns the latest release for the examples repository."""
        tags = sorted(
            self.repo.tags,
            key=lambda t: t.commit.committed_datetime,  # type: ignore
        )
        latest_tag = parse(tags[-1].name)
        if type(latest_tag) is not Version:
            return "main"
        return tags[-1].name  # type: ignore

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
        return os.path.join(self.examples_dir, EXAMPLES_RUN_SCRIPT)

    def clone(self) -> None:
        """Clones repo to cloning_path.

        If you break off the operation with a `KeyBoardInterrupt` before the
        cloning is completed, this method will delete whatever was partially
        downloaded from your system."""
        self.cloning_path.mkdir(parents=True, exist_ok=False)
        try:
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
        """Checks out a specific branch or tag of the examples repository

        Raises:
            GitCommandError: if branch doesn't exist.
        """
        logger.info(f"Checking out branch: {branch}")
        self.repo.git.checkout(branch)

    def checkout_latest_release(self) -> None:
        """Checks out the latest release of the examples repository."""
        self.checkout(self.latest_release)


class GitExamplesHandler(object):
    """Class for the GitExamplesHandler that interfaces with the CLI tool."""

    def __init__(self) -> None:
        """Create a new GitExamplesHandler instance."""
        self.repo_dir = zenml.io.utils.get_global_config_directory()
        self.examples_dir = Path(
            os.path.join(self.repo_dir, EXAMPLES_GITHUB_REPO)
        )
        self.examples_repo = ExamplesRepo(self.examples_dir)

    @property
    def examples(self) -> List[Example]:
        """Property that contains a list of examples"""
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
        example_dict = {e.name: e for e in self.examples}
        if example_name:
            if example_name in example_dict.keys():
                return [example_dict[example_name]]
            else:
                raise KeyError(
                    f"Example {example_name} does not exist! "
                    f"Available examples: {[example_dict.keys()]}"
                )
        else:
            return self.examples

    def pull(
        self, version: str = "", force: bool = False, branch: str = "main"
    ) -> None:
        """Pulls the examples from the main git examples repository."""
        if version == "":
            version = zenml_version_installed

        if not self.examples_repo.is_cloned:
            self.examples_repo.clone()
        elif force:
            self.examples_repo.delete()
            self.examples_repo.clone()

        try:
            if branch not in self.examples_repo.repo.references:
                warning(
                    f"The specified branch {branch} not found in "
                    "repo, falling back to use main."
                )
                branch = "main"
            if branch != "main":
                self.examples_repo.checkout(branch=branch)
            else:
                self.examples_repo.checkout(version)
        except GitCommandError:
            logger.warning(
                f"Version {version} does not exist in remote repository. "
                f"Reverting to `main`."
            )
            self.examples_repo.checkout("main")

    def pull_latest_examples(self) -> None:
        """Pulls the latest examples from the examples repository."""
        self.pull(version=self.examples_repo.latest_release, force=True)

    def copy_example(self, example: Example, destination_dir: str) -> None:
        """Copies an example to the destination_dir."""
        fileio.create_dir_if_not_exists(destination_dir)
        fileio.copy_dir(
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


@cli.group(help="Access all ZenML examples.")
def example() -> None:
    """Examples group"""


@example.command(help="List the available examples.")
@pass_git_examples_handler
def list(git_examples_handler: GitExamplesHandler) -> None:
    """List all available examples."""
    check_for_version_mismatch(git_examples_handler)
    declare("Listing examples: \n")

    for example in git_examples_handler.get_examples():
        declare(f"{example.name}")

    declare("\n" + "To pull the examples, type: ")
    declare("zenml example pull EXAMPLE_NAME")


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
        fileio.file_exists(examples_directory)
        and fileio.is_dir(examples_directory)
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
    elif not fileio.file_exists(examples_directory) and not fileio.is_dir(
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
    """Find out more about an example."""
    check_for_version_mismatch(git_examples_handler)
    # TODO [ENG-148]: fix markdown formatting so that it looks nicer (not a
    #  pure .md dump)
    try:
        example_obj = git_examples_handler.get_examples(example_name)[0]

    except KeyError as e:
        error(str(e))

    else:
        title(example_obj.name)
        pretty_print(example_obj.readme_content)


@example.command(
    help="Pull examples straight into your current working directory."
)
@pass_git_examples_handler
@click.argument("example_name", required=False, default=None)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Force the redownload of the examples folder to the ZenML config "
    "folder.",
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
    default="main",
    help="The branch of the ZenML repo to use for the force-redownloaded "
    "examples. A non main-branch overrules the version number.",
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
    version: str,
    path: str,
    branch: str,
) -> None:
    """Pull examples straight into your current working directory.
    Add the flag --force or -f to redownload all the examples afresh.
    Use the flag --version or -v and the version number to specify
    which version of ZenML you wish to use for the examples."""
    git_examples_handler.pull(
        force=force, version=version, branch=branch.strip()
    )

    examples_dir = os.path.join(os.getcwd(), path)
    fileio.create_dir_if_not_exists(examples_dir)
    try:
        examples = git_examples_handler.get_examples(example_name)

    except KeyError as e:
        error(str(e))

    else:
        for example in examples:
            destination_dir = os.path.join(os.getcwd(), path, example.name)

            if LocalExample(Path(example.name), destination_dir).is_present():
                if force or confirmation(
                    f"Example {example.name} is already pulled. "
                    "Do you wish to overwrite the directory at "
                    f"{destination_dir}?"
                ):
                    fileio.rm_dir(destination_dir)
                else:
                    warning(f"Example {example.name} not overwritten.")
                    continue

            declare(f"Pulling example {example.name}...")

            fileio.create_dir_if_not_exists(destination_dir)
            git_examples_handler.copy_example(example, destination_dir)
            declare(f"Example pulled in directory: {destination_dir}")


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
    "--force",
    "-f",
    is_flag=True,
    help="Force the run of the example. This deletes the .zen folder from the "
    "example folder and force installs all necessary integration "
    "requirements.",
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
    shell_executable: Optional[str],
) -> None:
    """Run the example at the specified relative path.
    `zenml example pull EXAMPLE_NAME` has to be called with the same relative
    path before the run command.
    """
    check_for_version_mismatch(git_examples_handler)

    # TODO [ENG-272]: - create a post_run function inside individual setup.sh
    #  to inform user how to clean up
    examples_dir = Path(os.getcwd()) / path
    try:
        _ = git_examples_handler.get_examples(example_name)[0]
    except KeyError as e:
        error(str(e))
    else:
        example_dir = examples_dir / example_name
        local_example = LocalExample(example_dir, example_name)

        if not local_example.is_present():
            ctx.forward(pull)

        example_runner = (
            [] if shell_executable is None else [shell_executable]
        ) + [git_examples_handler.examples_repo.examples_run_bash_script]
        try:
            local_example.run_example(
                example_runner=example_runner, force=force
            )
        except NotImplementedError as e:
            error(str(e))
