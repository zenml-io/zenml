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

import click

from zenml.cli import utils as cli_utils
from zenml.cli.stack import stack
from zenml.logger import get_logger
from zenml.mlstacks.utils import (
    get_mlstacks_version,
)
from zenml.recipes import GitStackRecipesHandler
from zenml.utils import yaml_utils

logger = get_logger(__name__)


pass_git_stack_recipes_handler = click.make_pass_decorator(
    GitStackRecipesHandler, ensure=True
)


@stack.group(
    "recipe",
    help="Commands for using the stack recipes.",
    invoke_without_command=True,
)
def stack_recipe() -> None:
    """Access all ZenML stack recipes."""


@stack_recipe.command(name="list", help="List the available stack recipes.")
def list_stack_recipes() -> None:
    """List all available stack recipes."""
    cli_utils.warning(
        "This command has been disabled and will be removed in a future "
        "release. Please refer to the `mlstacks` documentation for more "
        "information at https://mlstacks.zenml.io/"
    )


@stack_recipe.command(help="Deletes the ZenML stack recipes directory.")
@click.option(
    "--path",
    "-p",
    type=click.STRING,
    default="zenml_stack_recipes",
    help="Relative path at which you want to clean the stack_recipe(s)",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Whether to skip the confirmation prompt.",
)
def clean(
    path: str,
    yes: bool,
) -> None:
    """Deletes the stack recipes directory from your working directory.

    Args:
        path: The path at which you want to clean the stack_recipe(s).
        yes: Whether to skip the confirmation prompt.
    """
    cli_utils.warning(
        "This command has been disabled and will be removed in a future "
        "release. Please refer to the `mlstacks` documentation for more "
        "information at https://mlstacks.zenml.io/"
    )


@stack_recipe.command(help="Find out more about a stack recipe.")
@click.argument("stack_recipe_name")
def info(
    stack_recipe_name: str,
) -> None:
    """Find out more about a stack recipe.

    Outputs a pager view of the stack_recipe's README.md file.

    Args:
        stack_recipe_name: The name of the stack recipe.
    """
    recipe_readme = cli_utils.get_recipe_readme(stack_recipe_name)
    if recipe_readme is None:
        cli_utils.error(
            f"Unable to find stack recipe {stack_recipe_name}. "
            "Please check the name and try again."
        )
    cli_utils.print_markdown_with_pager(recipe_readme)


@stack_recipe.command(
    help="Describe the stack components and their tools that are "
    "created as part of this recipe."
)
@click.argument(
    "stack_recipe_name",
    type=click.Choice(("aws-modular", "gcp-modular", "k3d-modular")),
)
def describe(
    stack_recipe_name: str,
) -> None:
    """Describe the stack components and their tools that are created as part of this recipe.

    Outputs the "Description" section of the recipe metadata.

    Args:
        stack_recipe_name: The name of the stack recipe.
    """
    stack_recipe_path = cli_utils.get_recipe_path(stack_recipe_name)
    if stack_recipe_path is None:
        cli_utils.error(
            f"Unable to find stack recipe {stack_recipe_name}. "
            "Please check the name and try again."
        )
    recipe_metadata_yaml = os.path.join(stack_recipe_path, "metadata.yaml")
    recipe_metadata = yaml_utils.read_yaml(recipe_metadata_yaml)
    logger.info(recipe_metadata["Description"])


@stack_recipe.command(help="The active version of the mlstacks recipes.")
def version() -> None:
    """The active version of the mlstacks recipes."""
    if active_version := get_mlstacks_version():
        cli_utils.declare(f"Running `mlstacks` version {active_version}.")
    else:
        cli_utils.warning("Unable to detect version.")
