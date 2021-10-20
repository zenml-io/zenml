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
from typing import List

import click
from git import Repo

from zenml import __version__ as zenml_version_installed
from zenml.cli.cli import cli
from zenml.constants import APP_NAME, GIT_REPO_URL
from zenml.utils import path_utils

# TODO: [MEDIUM] Add an example-run command to run an example.

EXAMPLES_GITHUB_REPO = "zenml_examples"


# logit = get_logger(__name__)


class GitExamplesHandler(object):
    def __init__(self) -> None:
        self.clone_repo()

    def clone_repo(self) -> None:
        """Clone ZenML git repo into global config directory if not already cloned"""
        repo_dir = click.get_app_dir(APP_NAME)
        examples_dir = os.path.join(repo_dir, EXAMPLES_GITHUB_REPO)
        # get the files inside the global config directory
        config_directory_files = os.listdir(repo_dir)

        # check out the branch of the installed version even if we do have a local copy (minimal check)
        if EXAMPLES_GITHUB_REPO not in config_directory_files:
            installed_version = zenml_version_installed
            Repo.clone_from(
                GIT_REPO_URL, examples_dir, branch=installed_version
            )
        # if cloning cancels in the middle, try, but if keyboard interrupt, clean the directory
        # always want to give the option to clean the repo + redownload it (with a flag?)
        # clean + initiate function etc
        # ALSO: someone who wants to use a version of zenml which isn't their installed version

    def get_examples_dir(self) -> str:
        # TODO: [HIGH] move these functions into the GitExamplesHandler class
        # consider adding run-example command
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

    def get_example_readme(self, example_path) -> str:
        """Get the example README file contents."""
        with open(os.path.join(example_path, "README.md")) as readme:
            readme_content = readme.read()
        return readme_content


pass_git_examples_handler = click.make_pass_decorator(
    GitExamplesHandler, ensure=True
)


@cli.group(help="Access all ZenML examples.")
def example():
    """Examples group"""


@example.command(help="Test examples.")
@pass_git_examples_handler
def test(git_examples_handler):
    """Testing function"""
    click.echo("Testing examples: \n")


@example.command(help="List the available examples.")
@pass_git_examples_handler
def list(git_examples_handler):
    """List all available examples."""
    click.echo("Listing examples: \n")
    # git_examples_handler.get_all_examples()
    for name in git_examples_handler.get_all_examples():
        click.echo(f"{name}")
    click.echo("\nTo pull the examples, type: ")
    click.echo("zenml example pull EXAMPLE_NAME")


@example.command(help="Find out more about an example.")
@pass_git_examples_handler
@click.argument("example_name")
def info(git_examples_handler, example_name):
    """Find out more about an example."""
    # TODO: [MEDIUM] format the output so that it looks nicer (not a pure .md dump)
    example_dir = os.path.join(
        git_examples_handler.get_examples_dir(), example_name
    )
    readme_content = git_examples_handler.get_example_readme(example_dir)
    click.echo(readme_content)


@example.command(
    help="Pull examples straight into your current working directory."
)
@pass_git_examples_handler
@click.argument("example_name", required=False, default=None)
def pull(git_examples_handler, example_name):
    """Pull examples straight " "into your current working directory."""
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
            if click.confirm(
                f"Example {example} is already pulled. "
                f"Do you wish to overwrite the directory?"
            ):
                path_utils.rm_dir(dst_dir)
            else:
                continue
        click.echo(f"Pulling example {example}")
        src_dir = os.path.join(examples_dir, example)
        path_utils.copy_dir(src_dir, dst_dir)

        click.echo(f"Example pulled in directory: {dst_dir}")

    click.echo()
    click.echo(
        "Please read the README.md file in the respective example "
        "directory to find out more about the example"
    )
