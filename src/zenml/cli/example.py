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
"""Functionality to handle downloading ZenML examples via the CLI."""

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

import click
from rich.markdown import Markdown
from rich.text import Text

from zenml import __version__ as zenml_version_installed
from zenml.cli.cli import TagGroup, cli
from zenml.cli.utils import confirmation, declare, error, print_table, warning
from zenml.console import console
from zenml.constants import GIT_REPO_URL
from zenml.exceptions import GitNotFoundError
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.utils import io_utils
from zenml.utils.analytics_utils import AnalyticsEvent, event_handler

logger = get_logger(__name__)

EXCLUDED_EXAMPLE_DIRS = ["add_your_own"]
EXAMPLES_GITHUB_REPO = "zenml_examples"
EXAMPLES_RUN_SCRIPT = "run_example.sh"
SHELL_EXECUTABLE = "SHELL_EXECUTABLE"


class LocalExample:
    """Class to encapsulate the local example that can be run from the CLI."""

    def __init__(
        self, path: Path, name: str, skip_manual_check: bool = False
    ) -> None:
        """Create a new LocalExample instance.

        Args:
            name: The name of the example, specifically the name of the folder
                  on git
            path: Path at which the example is installed
            skip_manual_check: Whether to skip checking whether the example
                can be run manually or not.
        """
        self.name = name
        self.path = path
        self.skip_manual_check = skip_manual_check

    @property
    def python_files_in_dir(self) -> List[str]:
        """List of all Python files in the local example directory.

        The `__init__.py` file is excluded from this list.

        Returns:
            List of Python files in the local example directory.
        """
        py_in_dir = io_utils.find_files(str(self.path), "*.py")
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
        """Boolean that states if only one Python file is present.

        Returns:
            Whether only one Python file is present.
        """
        return len(self.python_files_in_dir) == 1

    @property
    def has_any_python_file(self) -> bool:
        """Boolean that states if any python file is present.

        Returns:
            Whether any Python file is present.
        """
        return len(self.python_files_in_dir) > 0

    @property
    def run_dot_py_file(self) -> Optional[str]:
        """Returns the path to the run.py file in case one exists.

        Returns:
            Path to the run.py file in case one exists.
        """
        for file in self.python_files_in_dir:
            # Make sure only files directly in dir are considered, not files
            # in sub dirs
            if self.path == Path(file).parent:
                if Path(file).name == "run.py":
                    return file
        return None

    @property
    def needs_manual_user_setup(self) -> bool:
        """Checks if a setup.sh file exists in the example dir.

        This indicates the possibility to run the example without any user
        input. Examples with no setup.sh file need the user to setup
        infrastructure and/or connect to tools/service providers.

        Returns:
            True if no setup.sh file in self.path, False else
        """
        return not fileio.exists(os.path.join(str(self.path), "setup.sh"))

    @property
    def executable_python_example(self) -> str:
        """Return the Python file for the example.

        Returns:
            The Python file for the example.

        Raises:
            RuntimeError: If no runner script is present in the example.
            NotImplementedError: If the examples needs manual user setup.
        """
        if not self.skip_manual_check and self.needs_manual_user_setup:
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
        """Checks if the example exists at the given path.

        Returns:
            True if the example exists at the given path, else False.
        """
        return fileio.exists(str(self.path)) and fileio.isdir(str(self.path))

    def run_example_directly(self, *args: str) -> None:
        """Runs the example directly without going through setup/teardown.

        Args:
            *args: Arguments to pass to the example.

        Raises:
            RuntimeError: If running the example fails.
        """
        with event_handler(
            event=AnalyticsEvent.RUN_EXAMPLE,
            metadata={"example_name": self.name},
        ):

            call = [sys.executable, self.executable_python_example, *args]
            try:
                subprocess.check_call(
                    call,
                    cwd=str(self.path),
                    shell=click._compat.WIN,
                    env=os.environ.copy(),
                )
            except Exception as e:
                raise RuntimeError(f"Failed to run example {self.name}.") from e

    def run_example(
        self,
        example_runner: List[str],
        force: bool,
        prevent_stack_setup: bool = False,
    ) -> None:
        """Run the local example using the bash script at the supplied location.

        Args:
            example_runner: Sequence of locations of executable file(s)
                            to run the example
            force: Whether to force the installation
            prevent_stack_setup: Prevents the example from setting up a custom
                stack.

        Raises:
            NotImplementedError: If the example hasn't been implement yet.
            FileNotFoundError: If the example runner script is not found.
            subprocess.CalledProcessError: If the example runner script fails.
        """
        with event_handler(
            event=AnalyticsEvent.RUN_EXAMPLE,
            metadata={"example_name": self.name},
        ):

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
                    "Bash File(s) to run Examples not found at"
                    f"{example_runner}"
                )


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
        """Returns the README content associated with a particular example.

        Returns:
            The README content associated with a particular example.

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
                    f"Example {self.name} is not one of the available options."
                    f"\n"
                    f"To list all available examples, type: `zenml example "
                    f"list`"
                )


class ExamplesRepo:
    """Class for the examples repository object."""

    def __init__(self, cloning_path: Path) -> None:
        """Create a new ExamplesRepo instance.

        Args:
            cloning_path: Path to the local examples repository.

        Raises:
            GitNotFoundError: If git is not installed.
        """
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
        except (NoSuchPathError, InvalidGitRepositoryError):
            self.repo = None  # type: ignore
            logger.debug(
                f"`Cloning_path`: {self.cloning_path} was empty, "
                "Automatically cloning the examples."
            )
            self.clone()
            self.checkout_latest_release()

    @property
    def active_version(self) -> Optional[str]:
        """Returns the active version of the examples repository.

        In case a release branch is checked out, this property returns
        that version as a string, else `None` is returned.

        Returns:
            The active version of the examples repository.
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
        latest_tag = parse(tags[-1].name)
        if type(latest_tag) is not Version:
            return "main"

        latest_release_version: str = tags[-1].name
        return f"release/{latest_release_version}"

    @property
    def is_cloned(self) -> bool:
        """Returns whether we have already cloned the examples repository.

        Returns:
            Whether we have already cloned the examples repository.
        """
        return self.cloning_path.exists()

    @property
    def examples_dir(self) -> str:
        """Returns the path for the examples directory.

        Returns:
            The path for the examples directory.
        """
        return os.path.join(self.cloning_path, "examples")

    @property
    def examples_run_bash_script(self) -> str:
        """Path to the bash script that runs the example.

        Returns:
            Path to the bash script that runs the example.
        """
        return os.path.join(self.examples_dir, EXAMPLES_RUN_SCRIPT)

    def clone(self) -> None:
        """Clones repo to `cloning_path`.

        If you break off the operation with a `KeyBoardInterrupt` before the
        cloning is completed, this method will delete whatever was partially
        downloaded from your system.
        """
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

    def pull(self) -> None:
        """Pull or clone the latest repository version."""
        if not self.cloning_path.exists():
            self.clone()
        else:
            logger.info("Fetching latest examples repository")
            self.repo.git.pull()

    def delete(self) -> None:
        """Delete `cloning_path` if it exists.

        Raises:
            AssertionError: If `cloning_path` does not exist.
        """
        if self.cloning_path.exists():
            shutil.rmtree(self.cloning_path)
        else:
            raise AssertionError(
                f"Cannot delete the examples repository from "
                f"{self.cloning_path} as it does not exist."
            )

    def checkout(self, branch: str) -> None:
        """Checks out a specific branch or tag of the examples repository.

        Args:
            branch: The name of the branch or tag to check out.
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
        self.repo_dir = io_utils.get_global_config_directory()
        self.examples_dir = Path(
            os.path.join(self.repo_dir, EXAMPLES_GITHUB_REPO)
        )
        self.examples_repo = ExamplesRepo(self.examples_dir)

    @property
    def examples(self) -> List[Example]:
        """Property that contains a list of examples.

        Returns:
            A list of examples.
        """
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
        """Checks whether examples are on the same code version as ZenML.

        Returns:
            Checks whether examples are on the same code version as ZenML.
        """
        return zenml_version_installed == str(self.examples_repo.active_version)

    def is_example(self, example_name: Optional[str] = None) -> bool:
        """Checks if the supplied example_name corresponds to an example.

        Args:
            example_name: The name of the example to check.

        Returns:
            Whether the supplied example_name corresponds to an example.
        """
        example_dict = {e.name: e for e in self.examples}
        if example_name:
            if example_name in example_dict.keys():
                return True

        return False

    def get_examples(self, example_name: Optional[str] = None) -> List[Example]:
        """Method that allows you to get an example by name.

        If no example is supplied,  all examples are returned.

        Args:
            example_name: Name of an example.

        Returns:
            A list of examples.

        Raises:
            KeyError: If the supplied example_name is not found.
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
        """Pulls the examples from the main git examples repository.

        Args:
            branch: The name of the branch to pull from.
            force: Whether to force the pull.
        """
        from git.exc import GitCommandError

        if self.examples_repo.is_cloned and force:
            self.examples_repo.delete()
        self.examples_repo.pull()

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

    @staticmethod
    def copy_example(example_: Example, destination_dir: str) -> None:
        """Copies an example to the destination_dir.

        Args:
            example_: The example to copy.
            destination_dir: The destination directory to copy the example to.
        """
        io_utils.create_dir_if_not_exists(destination_dir)
        io_utils.copy_dir(
            str(example_.path_in_repo), destination_dir, overwrite=True
        )

    @staticmethod
    def clean_current_examples() -> None:
        """Deletes the examples directory from the current working directory."""
        examples_directory = os.path.join(os.getcwd(), "zenml_examples")
        shutil.rmtree(examples_directory)


pass_git_examples_handler = click.make_pass_decorator(
    GitExamplesHandler, ensure=True
)


def check_for_version_mismatch(
    git_examples_handler: GitExamplesHandler,
) -> None:
    """Prints a warning if the example version and ZenML version don't match.

    Args:
        git_examples_handler: The GitExamplesHandler instance.
    """
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


@example.command(name="list", help="List the available examples.")
@pass_git_examples_handler
def list_examples(git_examples_handler: GitExamplesHandler) -> None:
    """List all available examples.

    Args:
        git_examples_handler: The GitExamplesHandler instance.
    """
    check_for_version_mismatch(git_examples_handler)
    examples = [
        {"example_name": example_.name}
        for example_ in git_examples_handler.get_examples()
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
    """Deletes the ZenML examples directory from your current working directory.

    Args:
        git_examples_handler: The GitExamplesHandler instance.
        path: The path at which you want to clean the example(s).
    """
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
    """Find out more about an example.

    Outputs a pager view of the example's README.md file.

    Args:
        git_examples_handler: The GitExamplesHandler instance.
        example_name: The name of the example.
    """
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
    which version of ZenML you wish to use for the examples.

    Args:
        git_examples_handler: The GitExamplesHandler instance.
        example_name: The name of the example.
        force: Force the redownload of the examples folder to the ZenML config
            folder.
        old_force: DEPRECATED: Force the redownload of the examples folder to
            the ZenML config folder.
        version: The version of ZenML to use for the force-redownloaded
            examples.
        path: The path at which you want to install the example(s).
        branch: The branch of the ZenML repo to use for the force-redownloaded
            examples.
    """
    if old_force:
        force = old_force
        warning(
            "The `--force` flag will soon be deprecated. Use `--yes` or "
            "`-y` instead."
        )

    branch = branch.strip() if branch else f"release/{version}"
    git_examples_handler.pull(branch=branch, force=force)

    examples_dir = os.path.join(os.getcwd(), path)
    io_utils.create_dir_if_not_exists(examples_dir)
    try:
        examples = git_examples_handler.get_examples(example_name)

    except KeyError as e:
        error(str(e))

    else:
        for example_ in examples:
            with event_handler(
                event=AnalyticsEvent.PULL_EXAMPLE,
                metadata={"example_name": example_.name},
            ):
                destination_dir = os.path.join(os.getcwd(), path, example_.name)
                if LocalExample(
                    name=example_.name, path=Path(destination_dir)
                ).is_present():
                    if force or confirmation(
                        f"Example {example_.name} is already pulled. "
                        "Do you wish to overwrite the directory at "
                        f"{destination_dir}?"
                    ):
                        fileio.rmtree(destination_dir)
                    else:
                        warning(f"Example {example_.name} not overwritten.")
                        continue

                declare(f"Pulling example {example_.name}...")

                io_utils.create_dir_if_not_exists(destination_dir)
                git_examples_handler.copy_example(example_, destination_dir)
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

    Args:
        ctx: The click context.
        git_examples_handler: The GitExamplesHandler instance.
        example_name: The name of the example.
        path: The path at which you want to install the example(s).
        force: Force the run of the example.
        old_force: DEPRECATED: Force the run of the example.
        shell_executable: Manually specify the path to the executable that
            runs .sh files.
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
