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


async def clone_zenml_repository(repo_dir: str) -> None:
    """Clone the zenml repository to a specific directory
    and checkout branch corresponding to the version
    of ZenML installed"""
    config_directory_files = os.listdir(repo_dir)

    if APP_NAME not in config_directory_files:
        installed_version = zenml_version_installed
        Repo.clone_from(GIT_REPO_URL, repo_dir, branch=installed_version)


def get_examples_dir() -> str:
    """Return the examples dir."""
    return os.path.join(click.get_app_dir(APP_NAME), APP_NAME, "examples")


async def get_all_examples() -> List[str]:
    """Get all the examples"""
    await clone_zenml_repository(click.get_app_dir(APP_NAME))

    return [
        name
        for name in sorted(os.listdir(get_examples_dir()))
        if (
            not name.startswith(".")
            and not name.startswith("__")
            and not name.startswith("README")
        )
    ]


def get_example_readme(example_path) -> str:
    """Get the example README file contents."""
    with open(os.path.join(example_path, "README.md")) as readme:
        readme_content = readme.read()
    return readme_content


@cli.group(help="Access all ZenML examples.")
def example():
    """Examples group"""


@example.command(help="List the available examples.")
def list():
    """List all available examples."""
    click.echo("Listing examples: \n")
    for name in get_all_examples():
        click.echo(f"{name}")
    click.echo("\nTo pull the examples, type: ")
    click.echo("zenml example pull EXAMPLE_NAME")


@example.command(help="Find out more about an example.")
@click.argument("example_name")
def info(example_name):
    """Find out more about an example."""
    example_dir = os.path.join(get_examples_dir(), example_name)
    readme_content = get_example_readme(example_dir)
    click.echo(readme_content)


@example.command(
    help="Pull examples straight " "into your current working directory."
)
@click.argument("example_name", required=False, default=None)
def pull(example_name):
    """Pull examples straight " "into your current working directory."""
    examples_dir = get_examples_dir()
    examples = get_all_examples() if not example_name else [example_name]
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
