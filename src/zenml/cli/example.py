#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.

#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:

#       http://www.apache.org/licenses/LICENSE-2.0

#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.

import os
import shutil
from pathlib import Path
from typing import List

import click
from git.exc import GitCommandError, NoSuchPathError
from git.repo.base import Repo
from packaging.version import Version, parse

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
from zenml.constants import APP_NAME, GIT_REPO_URL
from zenml.io import fileio
from zenml.logger import get_logger

logger = get_logger(__name__)

EXAMPLES_GITHUB_REPO = "zenml_examples"


class Example:
    """Class for all example objects."""

    def __init__(self, name: str, path: Path) -> None:
        """Create a new Example instance."""
        self.name = name
        self.path = path

    @property
    def readme_content(self) -> str:
        """Returns the readme content associated with a particular example."""
        readme_file = os.path.join(self.path, "README.md")
        try:
            with open(readme_file) as readme:
                readme_content = readme.read()
            return readme_content
        except FileNotFoundError:
            if fileio.file_exists(str(self.path)) and fileio.is_dir(
                str(self.path)
            ):
                raise ValueError(f"No README.md file found in {self.path}")
            else:
                raise FileNotFoundError(
                    f"Example {self.name} is not one of the available options."
                    f"\nTo list all available examples, type: `zenml example "
                    f"list`"
                )

    def run(self) -> None:
        """Runs the example script.

        Raises:
            NotImplementedError: This method is not yet implemented."""
        # TODO [ENG-191]: Add an example-run command to run an example. (ENG-145)
        raise NotImplementedError("Functionality is not yet implemented.")


class ExamplesRepo:
    """Class for the examples repository object."""

    def __init__(self, cloning_path: Path) -> None:
        """Create a new ExamplesRepo instance."""
        self.cloning_path = cloning_path
        try:
            self.repo = Repo(self.cloning_path)
        except NoSuchPathError:
            self.repo = None  # type: ignore
            logger.debug(
                f"`cloning_path`: {self.cloning_path} was empty, "
                f"but ExamplesRepo was created. "
                "Ensure a pull is performed before doing any other operations."
            )

    @property
    def latest_release(self) -> str:
        """Returns the latest release for the examples repository."""
        tags = sorted(
            self.repo.tags, key=lambda t: t.commit.committed_datetime  # type: ignore
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
            logger.error("Cancelled download of repository.. Rolled back.")

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
        repo_dir = click.get_app_dir(APP_NAME)
        examples_dir = Path(os.path.join(repo_dir, EXAMPLES_GITHUB_REPO))
        self.examples_repo = ExamplesRepo(examples_dir)

    @property
    def examples(self) -> List[Example]:
        """Returns a list of examples"""
        return [
            Example(
                name, Path(os.path.join(self.examples_repo.examples_dir, name))
            )
            for name in sorted(os.listdir(self.examples_repo.examples_dir))
            if (
                not name.startswith(".")
                and not name.startswith("__")
                and not name.startswith("README")
            )
        ]

    def pull(self, version: str = "", force: bool = False) -> None:
        """Pulls the examples from the main git examples repository."""
        if version == "":
            version = self.examples_repo.latest_release

        if not self.examples_repo.is_cloned:
            self.examples_repo.clone()
        elif force:
            self.examples_repo.delete()
            self.examples_repo.clone()

        try:
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
        fileio.copy_dir(str(example.path), destination_dir, overwrite=True)

    def clean_current_examples(self) -> None:
        """Deletes the ZenML examples directory from your current working
        directory."""
        examples_directory = os.path.join(os.getcwd(), "zenml_examples")
        shutil.rmtree(examples_directory)


pass_git_examples_handler = click.make_pass_decorator(
    GitExamplesHandler, ensure=True
)


@cli.group(help="Access all ZenML examples.")
def example() -> None:
    """Examples group"""


@example.command(help="List the available examples.")
@pass_git_examples_handler
def list(git_examples_handler: GitExamplesHandler) -> None:
    """List all available examples."""
    declare("Listing examples: \n")
    for example in git_examples_handler.examples:
        declare(f"{example.name}")
    declare("\nTo pull the examples, type: ")
    declare("zenml example pull EXAMPLE_NAME")


@example.command(help="Deletes the ZenML examples directory.")
@pass_git_examples_handler
def clean(git_examples_handler: GitExamplesHandler) -> None:
    """Deletes the ZenML examples directory from your current working
    directory."""
    examples_directory = os.path.join(os.getcwd(), "zenml_examples")
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
    # TODO [ENG-148]: fix markdown formatting so that it looks nicer (not a
    #  pure .md dump)
    example_obj = None
    for example in git_examples_handler.examples:
        if example.name == example_name:
            example_obj = example

    if example_obj is None:
        error(
            f"Example {example_name} is not one of the available options."
            f"\nTo list all available examples, type: `zenml example list`"
        )
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
def pull(
    git_examples_handler: GitExamplesHandler,
    example_name: str,
    force: bool,
    version: str,
) -> None:
    """Pull examples straight into your current working directory.
    Add the flag --force or -f to redownload all the examples afresh.
    Use the flag --version or -v and the version number to specify
    which version of ZenML you wish to use for the examples."""
    git_examples_handler.pull(force=force, version=version)
    destination_dir = os.path.join(os.getcwd(), "zenml_examples")
    fileio.create_dir_if_not_exists(destination_dir)

    examples = (
        git_examples_handler.examples
        if not example_name
        else [
            Example(
                example_name,
                Path(
                    os.path.join(
                        git_examples_handler.examples_repo.examples_dir,
                        example_name,
                    )
                ),
            )
        ]
    )

    for example in examples:
        if not fileio.file_exists(str(example.path)):
            error(
                f"Example {example.name} does not exist! Available examples: "
                f"{[e.name for e in git_examples_handler.examples]}"
            )
            return

        example_destination_dir = os.path.join(destination_dir, example.name)
        if fileio.file_exists(example_destination_dir):
            if confirmation(
                f"Example {example.name} is already pulled. "
                f"Do you wish to overwrite the directory?"
            ):
                fileio.rm_dir(example_destination_dir)
            else:
                warning(f"Example {example.name} not overwritten.")
                continue

        declare(f"Pulling example {example.name}...")
        git_examples_handler.copy_example(example, example_destination_dir)

        declare(f"Example pulled in directory: {example_destination_dir}")
