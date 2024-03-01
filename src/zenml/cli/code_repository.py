#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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

from typing import Any, List, Optional

import click

from zenml.cli import utils as cli_utils
from zenml.cli.cli import TagGroup, cli
from zenml.cli.utils import list_options
from zenml.client import Client
from zenml.code_repositories import BaseCodeRepository
from zenml.config.source import Source
from zenml.console import console
from zenml.enums import CliCategories
from zenml.logger import get_logger
from zenml.models import CodeRepositoryFilter
from zenml.utils import source_utils

logger = get_logger(__name__)


@cli.group(cls=TagGroup, tag=CliCategories.MANAGEMENT_TOOLS)
def code_repository() -> None:
    """Interact with code repositories."""


@code_repository.command(
    "register",
    context_settings={"ignore_unknown_options": True},
    help="Register a code repository.",
)
@click.argument("name", type=click.STRING)
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
    "source_path",
    type=str,
    required=False,
    help="Module containing the code repository implementation if type is custom.",
)
@click.option(
    "--description",
    "-d",
    type=str,
    required=False,
    help="The code repository description.",
)
@click.option(
    "--logo-url",
    "-l",
    type=str,
    required=False,
    help="URL of a logo (png, jpg or svg) for the code repository.",
)
@click.argument(
    "args",
    nargs=-1,
    type=click.UNPROCESSED,
)
def register_code_repository(
    name: str,
    type_: str,
    source_path: Optional[str],
    description: Optional[str],
    logo_url: Optional[str],
    args: List[str],
) -> None:
    """Register a code repository.

    Register a code repository with ZenML. This will allow ZenML to pull
    code from a remote repository and use it when running pipelines remotely.
    The configuration of the code repository can be different depending on the
    type of code repository. For more information, please refer to the
    documentation.

    Args:
        name: Name of the code repository
        type_: Type of the code repository
        source_path: Path to the source module if type is custom
        description: The code repository description.
        logo_url: URL of a logo (png, jpg or svg) for the code repository.
        args: Additional arguments to be passed to the code repository
    """
    parsed_name, parsed_args = cli_utils.parse_name_and_extra_arguments(
        list(args) + [name], expand_args=True
    )
    assert parsed_name
    name = parsed_name

    if type_ == "github":
        try:
            from zenml.integrations.github.code_repositories import (
                GitHubCodeRepository,
            )
        except ImportError:
            cli_utils.error(
                "You need to install the GitHub integration to use a GitHub "
                "code repository. Please run `zenml integration install "
                "github` and try again."
            )
        source = source_utils.resolve(GitHubCodeRepository)
    elif type_ == "gitlab":
        try:
            from zenml.integrations.gitlab.code_repositories import (
                GitLabCodeRepository,
            )
        except ImportError:
            cli_utils.error(
                "You need to install the GitLab integration to use a GitLab "
                "code repository. Please run `zenml integration install "
                "gitlab` and try again."
            )
        source = source_utils.resolve(GitLabCodeRepository)
    elif type_ == "custom":
        if not source_path:
            cli_utils.error(
                "When using a custom code repository type, you need to provide "
                "a path to the implementation class using the --source option: "
                "`zenml code-repository register --type=custom --source=<...>"
            )
        if not source_utils.validate_source_class(
            source_path, expected_class=BaseCodeRepository
        ):
            cli_utils.error(
                f"Your source {source_path} does not point to a "
                f"`{BaseCodeRepository.__name__}` subclass and can't be used "
                "to register a code repository."
            )

        source = Source.from_import_path(source_path)

    with console.status(f"Registering code repository '{name}'...\n"):
        Client().create_code_repository(
            name=name,
            config=parsed_args,
            source=source,
            description=description,
            logo_url=logo_url,
        )

        cli_utils.declare(f"Successfully registered code repository `{name}`.")


@code_repository.command("list", help="List all connected code repositories.")
@list_options(CodeRepositoryFilter)
def list_code_repositories(**kwargs: Any) -> None:
    """List all connected code repositories.

    Args:
        **kwargs: Keyword arguments to filter code repositories.
    """
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
