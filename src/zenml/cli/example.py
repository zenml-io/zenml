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
from pathlib import Path
from typing import Any, List

import click
from git.exc import GitCommandError
from git.repo.base import Repo
from packaging.version import parse

from zenml import __version__ as zenml_version_installed
from zenml.cli.cli import cli
from zenml.cli.utils import confirmation, declare, error, warning
from zenml.constants import APP_NAME, GIT_REPO_URL
from zenml.utils import path_utils

# TODO: [MEDIUM] Add an example-run command to run an example.

EXAMPLES_GITHUB_REPO = "zenml_examples"


class GitExamplesHandler(object):
    """Handles logic related to cloning and checking out the ZenML Git
    repository, in relation to the `examples` dir."""

    def __init__(self, redownload: str = "") -> None:
        """Initialize the GitExamplesHandler class."""
        self.clone_repo(redownload)

    def clone_repo(self, redownload_version: str = "") -> None:
        """Clone ZenML git repo into global config directory if not already
        cloned"""
        installed_version = zenml_version_installed
        repo_dir = click.get_app_dir(APP_NAME)
        examples_dir = os.path.join(repo_dir, EXAMPLES_GITHUB_REPO)
        # delete source directory if force redownload is set
        if redownload_version:
            self.delete_example_source_dir(examples_dir)
            installed_version = redownload_version

        config_directory_files = os.listdir(repo_dir)

        if (
            redownload_version
            or EXAMPLES_GITHUB_REPO not in config_directory_files
        ):
            self.clone_from_zero(GIT_REPO_URL, examples_dir)
            repo = Repo(examples_dir)
            self.checkout_repository(repo, installed_version)

    def clone_from_zero(self, git_repo_url: str, local_dir: str) -> None:
        """Basic functionality to clone a repo."""
        try:
            Repo.clone_from(git_repo_url, local_dir, branch="main")
        except KeyboardInterrupt:
            self.delete_example_source_dir(local_dir)
            error("Cancelled download of repository.. Rolled back.")
            return

    def checkout_repository(
        self,
        repository: Repo,
        desired_version: str,
        fallback_to_latest: bool = True,
    ) -> None:
        """Checks out a branch or tag of a git repository

        Args:
            repository: a Git repository reference.
            desired_version: a valid ZenML release version number.
            fallback_to_latest: Whether to default to the latest released
            version or not if `desired_version` does not exist.
        """
        try:
            repository.git.checkout(desired_version)
        except GitCommandError:
            if fallback_to_latest:
                last_release = parse(repository.tags[-1].name)
                repository.git.checkout(last_release)
                warning(
                    f"You just tried to download examples for version "
                    f"{desired_version}. "
                    f"There is no corresponding release or version. We are "
                    f"going to "
                    f"default to the last release: {last_release}"
                )
            else:
                error(
                    f"You just tried to checkout the repository for version "
                    f"{desired_version}. "
                    f"There is no corresponding release or version. Please try "
                    f"again with a version number corresponding to an actual "
                    f"release."
                )
                raise

    def clone_when_examples_already_cloned(
        self, local_dir: str, version: str
    ) -> None:
        """Basic functionality to clone the ZenML examples
        into the global config directory if they are already cloned."""
        local_dir_path = Path(local_dir)
        repo = Repo(str(local_dir_path))
        desired_version = parse(version)
        self.delete_example_source_dir(str(local_dir_path))
        self.clone_from_zero(GIT_REPO_URL, local_dir)
        self.checkout_repository(
            repo, str(desired_version), fallback_to_latest=False
        )

    def get_examples_dir(self) -> str:
        """Return the examples dir"""
        return os.path.join(
            click.get_app_dir(APP_NAME), EXAMPLES_GITHUB_REPO, "examples"
        )

    def get_all_examples(self) -> List[str]:
        """Get all the examples"""
        return [
            name
            for name in sorted(os.listdir(self.get_examples_dir()))
            if (
                not name.startswith(".")
                and not name.startswith("__")
                and not name.startswith("README")
            )
        ]

    def get_example_readme(self, example_path: str) -> str:
        """Get the example README file contents.

        Raises:
            FileNotFoundError: if the file doesn't exist.
        """
        with open(os.path.join(example_path, "README.md")) as readme:
            readme_content = readme.read()
        return readme_content

    def delete_example_source_dir(self, source_path: str) -> None:
        """Clean the example directory. This method checks that we are
        inside the ZenML config directory before performing its deletion.

        Args:
            source_path (str): The path to the example source directory.

        Raises:
            ValueError: If the source_path is not the ZenML config directory.
        """
        config_directory_path = str(
            os.path.join(click.get_app_dir(APP_NAME), EXAMPLES_GITHUB_REPO)
        )
        if source_path == config_directory_path:
            path_utils.rm_dir(source_path)
        else:
            raise ValueError(
                "You can only delete the source directory from your ZenML "
                "config directory"
            )

    def delete_working_directory_examples_folder(self) -> None:
        """Delete the zenml_examples folder from the current working
        directory."""
        cwd_directory_path = os.path.join(os.getcwd(), EXAMPLES_GITHUB_REPO)
        if os.path.exists(cwd_directory_path):
            path_utils.rm_dir(str(cwd_directory_path))


pass_git_examples_handler = click.make_pass_decorator(
    GitExamplesHandler, ensure=True
)


@cli.group(help="Access all ZenML examples.")
def example() -> None:
    """Examples group"""


@example.command(help="List the available examples.")
@pass_git_examples_handler
# TODO: [MEDIUM] Use a better type for the git_examples_handler
def list(git_examples_handler: Any) -> None:
    """List all available examples."""
    declare("Listing examples: \n")
    for name in git_examples_handler.get_all_examples():
        declare(f"{name}")
    declare("\nTo pull the examples, type: ")
    declare("zenml example pull EXAMPLE_NAME")


@example.command(help="Find out more about an example.")
@pass_git_examples_handler
@click.argument("example_name")
# TODO: [MEDIUM] Use a better type for the git_examples_handler
def info(git_examples_handler: Any, example_name: str) -> None:
    """Find out more about an example."""
    # TODO: [MEDIUM] fix markdown formatting so that it looks nicer (not a
    #  pure .md dump)
    example_dir = os.path.join(
        git_examples_handler.get_examples_dir(), example_name
    )
    try:
        readme_content = git_examples_handler.get_example_readme(example_dir)
        click.echo(readme_content)
    except FileNotFoundError:
        if path_utils.file_exists(example_dir) and path_utils.is_dir(
            example_dir
        ):
            error(f"No README.md file found in {example_dir}")
        else:
            error(
                f"Example {example_name} is not one of the available options."
                f"\nTo list all available examples, type: `zenml example list`"
            )


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
# TODO: [MEDIUM] Use a better type for the git_examples_handler
def pull(
    git_examples_handler: Any,
    example_name: str,
    force: bool,
    version: str,
) -> None:
    """Pull examples straight into your current working directory.
    Add the flag --force or -f to redownload all the examples afresh.
    Use the flag --version or -v and the version number to specify
    which version of ZenML you wish to use for the examples."""
    if force:
        repo_dir = click.get_app_dir(APP_NAME)
        examples_dir = os.path.join(repo_dir, EXAMPLES_GITHUB_REPO)
        declare(f"Recloning ZenML repo for version {version}...")
        git_examples_handler.clone_when_examples_already_cloned(
            examples_dir, version
        )
        warning("Deleting examples from current working directory...")
        git_examples_handler.delete_working_directory_examples_folder()

    examples_dir = git_examples_handler.get_examples_dir()
    examples = (
        git_examples_handler.get_all_examples()
        if not example_name
        else [example_name]
    )
    # Create destination dir.
    dst = os.path.join(os.getcwd(), "zenml_examples")
    path_utils.create_dir_if_not_exists(dst)

    # Pull specified examples.
    for example in examples:
        dst_dir = os.path.join(dst, example)
        # Check if example has already been pulled before.
        if path_utils.file_exists(dst_dir):
            if confirmation(
                f"Example {example} is already pulled. "
                f"Do you wish to overwrite the directory?"
            ):
                path_utils.rm_dir(dst_dir)

        declare(f"Pulling example {example}...")
        src_dir = os.path.join(examples_dir, example)
        path_utils.copy_dir(src_dir, dst_dir)

        declare(f"Example pulled in directory: {dst_dir}")

    declare("")
    declare(
        "Please read the README.md file in the respective example "
        "directory to find out more about the example"
    )
