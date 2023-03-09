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
"""CLI functionality to interact with code repositories."""
import os
from typing import Any, List

import click

from zenml.cli import utils as cli_utils
from zenml.cli.cli import TagGroup, cli
from zenml.cli.utils import list_options
from zenml.client import Client
from zenml.config.source import Source, SourceType
from zenml.console import console
from zenml.enums import CliCategories
from zenml.exceptions import EntityExistsError
from zenml.logger import get_logger
from zenml.models import CodeRepositoryFilterModel

logger = get_logger(__name__)


@cli.group(cls=TagGroup, tag=CliCategories.MANAGEMENT_TOOLS)
def code_repository() -> None:
    """Interact with code repositories."""


@code_repository.command(
    "connect",
    help="Connect a code repository.",
)
@click.option(
    "--type",
    "-t",
    "type_",
    type=click.Choice(["github", "gitlab", "custom"]),
    required=True,
    help="Type of the code repository.",
)
@click.option(
    "--source",
    "-s",
    type=str,
    required=False,
    help="Module containing the code repository implementation.",
)
@click.argument("name")
@click.argument(
    "args",
    nargs=-1,
    type=click.UNPROCESSED,
)
def connect_code_repository(
    name: str,
    type_: str,
    source: str,
    args: List[str],
) -> None:
    """Connect a code repository

    Args:
        name: Name of the code repository
    """
    cli_utils.print_active_config()
    if type_ == "custom":
        if not source:
            cli_utils.error(
                "Please provide a path to the custom source module."
            )
        if not os.path.exists(source):
            cli_utils.error(
                "Please provide a valid path to the custom source module."
            )

    # Parse the given args
    # name is guaranteed to be set by parse_name_and_extra_arguments
    name, parsed_args = cli_utils.parse_name_and_extra_arguments(  # type: ignore[assignment]
        list(args) + [name], expand_args=True
    )

    if "name" in parsed_args:
        cli_utils.error(
            "You can't use 'name' as the key for one of your secrets."
        )
    elif name == "name":
        cli_utils.error("Secret names cannot be named 'name'.")
    try:
        source = Source(
            module="zenml.integrations.github.code_repositories",
            attribute="GitHubCodeRepository",
            type=SourceType.UNKNOWN,
        )
        Client().create_code_repository(
            name=name, config=parsed_args, source=source
        )
    except EntityExistsError as e:
        cli_utils.error(str(e))
    else:
        cli_utils.declare(f"Connected to code repository {name}.")


@code_repository.command("list", help="List all connected code repositories.")
@list_options(CodeRepositoryFilterModel)
def list_code_repositories(**kwargs: Any) -> None:
    """List all connected code repositories.

    Args:
        **kwargs: Keyword arguments to filter code repositories.
    """
    cli_utils.print_active_config()
    with console.status("Listing code repositories...\n"):
        repos = Client().list_code_repositories(**kwargs)

        if not repos.items:
            cli_utils.declare("No code repositories found for this filter.")
            return

        cli_utils.print_pydantic_models(
            repos,
            exclude_columns=["created", "updated", "user", "workspace"],
        )


@code_repository.command("delete")
@click.argument("name_or_id", type=str, required=True)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Don't ask for confirmation.",
)
def delete_code_repository(name_or_id: str, yes: bool = False) -> None:
    """Delete a code repository.

    Args:
        name_or_id: The name or ID of the code repository to delete.
        yes: If set, don't ask for confirmation.
    """
    cli_utils.print_active_config()

    if not yes:
        confirmation = cli_utils.confirmation(
            f"Are you sure you want to delete code repository `{name_or_id}`?"
        )
        if not confirmation:
            cli_utils.declare("Code repository deletion canceled.")
            return

    try:
        Client().delete_code_repository(name_id_or_prefix=name_or_id)
    except KeyError as e:
        cli_utils.error(str(e))
    else:
        cli_utils.declare(f"Deleted code repository `{name_or_id}`.")
