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
"""CLI functionality to interact with API keys."""
from typing import Any, Optional

import click

from zenml.cli import utils as cli_utils
from zenml.cli.cli import TagGroup, cli
from zenml.cli.utils import list_options
from zenml.client import Client
from zenml.console import console
from zenml.enums import CliCategories, StoreType
from zenml.exceptions import EntityExistsError
from zenml.logger import get_logger
from zenml.models import APIKeyFilterModel

logger = get_logger(__name__)


@cli.group(cls=TagGroup, tag=CliCategories.MANAGEMENT_TOOLS)
def api_key() -> None:
    """Interact with API keys."""


@api_key.command(
    "create",
    help="Create an API key and print its value.",
)
@click.argument("name", type=click.STRING)
@click.option(
    "--description",
    "-d",
    type=str,
    required=False,
    help="The API key description.",
)
@click.option(
    "--set",
    is_flag=True,
    help="Configure the local client with the generated key.",
)
def create_api_key(
    name: str,
    description: Optional[str],
    set: bool = False,
) -> None:
    """Create an API key.

    Args:
        name: Name of the API key
        description: The API key description.
        set: Configure the local client with the generated key.
    """
    client = Client()
    zen_store = client.zen_store
    if not zen_store.TYPE == StoreType.REST:
        raise NotImplementedError(
            "API key configuration is only supported if connected to a "
            "ZenML server."
        )

    with console.status(f"Creating API key '{name}'...\n"):
        try:
            api_key = client.create_api_key(
                name=name,
                description=description or "",
                set=set,
            )
        except EntityExistsError as e:
            cli_utils.error(str(e))

        cli_utils.declare(f"Successfully created API key `{name}`.")

    if not set:
        set = cli_utils.confirmation(
            "Would you like to configure the local client with the generated "
            "API key?"
        )

    if set and api_key.key:
        client.set_api_key(api_key.key)
        cli_utils.declare(
            "The local client has been configured with the new API key."
        )
    else:
        cli_utils.declare(
            f"The API key value is: '{api_key.key}'\nPlease store it safely as "
            "it will not be shown again.\nTo configure a ZenML client to use "
            "this API key, run:\n\n"
            f"zenml connect --url {zen_store.config.url} --api-key \\\n"
            f"    '{api_key.key}'\n"
        )


@api_key.command("describe", help="Describe an API key.")
@click.argument("name_or_id", type=str, required=True)
def describe_api_key(name_or_id: str) -> None:
    """Describe an API key.

    Args:
        name_or_id: The name or ID of the API key to describe.
    """
    with console.status(f"Getting API key `{name_or_id}`...\n"):
        try:
            api_key = Client().get_api_key(name_id_or_prefix=name_or_id)
        except KeyError as e:
            cli_utils.error(str(e))

    cli_utils.pretty_print_api_key(api_key)


@api_key.command("list", help="List all API keys.")
@list_options(APIKeyFilterModel)
def list_api_keys(**kwargs: Any) -> None:
    """List all API keys.

    Args:
        **kwargs: Keyword arguments to filter API keys.
    """
    with console.status("Listing API keys...\n"):
        api_keys = Client().list_api_keys(**kwargs)

        if not api_keys.items:
            cli_utils.declare("No API keys found for this filter.")
            return

        cli_utils.print_pydantic_models(
            api_keys,
            exclude_columns=[
                "created",
                "updated",
                "workspace",
                "key",
                "retain_period_minutes",
            ],
        )


@api_key.command("update", help="Update an API key.")
@click.argument("name_or_id", type=str, required=True)
@click.option("--name", type=str, required=False, help="The new name.")
@click.option(
    "--description", type=str, required=False, help="The new description."
)
@click.option(
    "--active",
    type=bool,
    required=False,
    help="Set an API key to active/inactive.",
)
def update_api_key(
    name_or_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    active: Optional[bool] = None,
) -> None:
    """Update an API key.

    Args:
        name_or_id: The name or ID of the API key to update.
        name: The new name of the API key.
        description: The new description of the API key.
        active: Set an API key to active/inactive.
    """
    try:
        Client().update_api_key(
            name_id_or_prefix=name_or_id,
            name=name,
            description=description,
            active=active,
        )
    except KeyError as e:
        cli_utils.error(str(e))

    cli_utils.declare(f"Successfully updated API key `{name_or_id}`.")


@api_key.command("rotate", help="Rotate an API key.")
@click.argument("name_or_id", type=str, required=True)
@click.option(
    "--retain",
    type=int,
    required=False,
    default=0,
    help="Number of minutes for which the previous key is still valid after it "
    "has been rotated.",
)
@click.option(
    "--set",
    is_flag=True,
    help="Configure the local client with the generated key.",
)
def rotate_api_key(
    name_or_id: str, retain: int = 0, set: bool = False
) -> None:
    """Rotate an API key.

    Args:
        name_or_id: The name or ID of the API key to rotate.
        retain: Number of minutes for which the previous key is still valid
            after it has been rotated.
        set: Configure the local client with the newly generated key.
    """
    client = Client()
    try:
        api_key = client.rotate_api_key(name_id_or_prefix=name_or_id, set=set)
    except KeyError as e:
        cli_utils.error(str(e))

    cli_utils.declare(f"Successfully rotated API key `{name_or_id}`.")
    if retain:
        cli_utils.declare(
            f"The previous API key will remain valid for {retain} minutes."
        )

    if not set:
        set = cli_utils.confirmation(
            "Would you like to configure the local client with the newly "
            "generated API key?"
        )

    if set and api_key.key:
        client.set_api_key(api_key.key)
        cli_utils.declare(
            "The local client has been configured with the new API key."
        )
    else:
        cli_utils.declare(
            f"The new API key value is: '{api_key.key}'\nPlease store it "
            "safely as it will not be shown again.\nTo configure a ZenML "
            "client to use this API key, run:\n\n"
            f"zenml connect --url <zenml-server-URL> --api-key {api_key.key}\n"
        )


@api_key.command("delete")
@click.argument("name_or_id", type=str, required=True)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Don't ask for confirmation.",
)
def delete_api_key(name_or_id: str, yes: bool = False) -> None:
    """Delete an API key.

    Args:
        name_or_id: The name or ID of the API key to delete.
        yes: If set, don't ask for confirmation.
    """
    if not yes:
        confirmation = cli_utils.confirmation(
            f"Are you sure you want to delete API key `{name_or_id}`?"
        )
        if not confirmation:
            cli_utils.declare("API key deletion canceled.")
            return

    try:
        Client().delete_api_key(name_id_or_prefix=name_or_id)
    except KeyError as e:
        cli_utils.error(str(e))
    else:
        cli_utils.declare(f"Deleted API key `{name_or_id}`.")
