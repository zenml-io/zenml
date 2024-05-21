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
from zenml.exceptions import EntityExistsError, IllegalOperationError
from zenml.logger import get_logger
from zenml.models import APIKeyFilter, ServiceAccountFilter

logger = get_logger(__name__)


def _create_api_key(
    service_account_name_or_id: str,
    name: str,
    description: Optional[str],
    set_key: bool = False,
) -> None:
    """Create an API key.

    Args:
        service_account_name_or_id: The name or ID of the service account to
            which the API key should be added.
        name: Name of the API key
        description: The API key description.
        set_key: Configure the local client with the generated key.
    """
    client = Client()
    zen_store = client.zen_store

    with console.status(f"Creating API key '{name}'...\n"):
        try:
            api_key = client.create_api_key(
                service_account_name_id_or_prefix=service_account_name_or_id,
                name=name,
                description=description or "",
            )
        except (KeyError, EntityExistsError) as e:
            cli_utils.error(str(e))

        cli_utils.declare(f"Successfully created API key `{name}`.")

    if set_key and api_key.key:
        if zen_store.TYPE != StoreType.REST:
            cli_utils.warning(
                "Could not configure the local ZenML client with the generated "
                "API key. This type of authentication is only supported if "
                "connected to a ZenML server."
            )
        else:
            client.set_api_key(api_key.key)
            cli_utils.declare(
                "The local client has been configured with the new API key."
            )
            return

    cli_utils.declare(
        f"The API key value is: '{api_key.key}'\nPlease store it safely as "
        "it will not be shown again.\nTo configure a ZenML client to use "
        "this API key, run:\n\n"
        f"zenml connect --url {zen_store.config.url} --api-key \\\n"
        f"    '{api_key.key}'\n"
    )


@cli.group(cls=TagGroup, tag=CliCategories.IDENTITY_AND_SECURITY)
def service_account() -> None:
    """Commands for service account management."""


@service_account.command(
    "create", help="Create a new service account and optional API key."
)
@click.argument("service_account_name", type=str, required=True)
@click.option(
    "--description",
    "-d",
    type=str,
    required=False,
    default="",
    help="The API key description.",
)
@click.option(
    "--create-api-key",
    help=("Create an API key for the service account."),
    type=bool,
    default=True,
)
@click.option(
    "--set-api-key",
    help=("Configure the local client to use the generated API key."),
    is_flag=True,
)
def create_service_account(
    service_account_name: str,
    description: str = "",
    create_api_key: bool = True,
    set_api_key: bool = False,
) -> None:
    """Create a new service account.

    Args:
        service_account_name: The name of the service account to create.
        description: The API key description.
        create_api_key: Create an API key for the service account.
        set_api_key: Configure the local client to use the generated API key.
    """
    client = Client()
    try:
        service_account = client.create_service_account(
            name=service_account_name,
            description=description,
        )

        cli_utils.declare(f"Created service account '{service_account.name}'.")
    except EntityExistsError as err:
        cli_utils.error(str(err))

    if create_api_key:
        _create_api_key(
            service_account_name_or_id=service_account.name,
            name="default",
            description="Default API key.",
            set_key=set_api_key,
        )


@service_account.command("describe")
@click.argument("service_account_name_or_id", type=str, required=True)
def describe_service_account(service_account_name_or_id: str) -> None:
    """Describe a service account.

    Args:
        service_account_name_or_id: The name or ID of the service account.
    """
    client = Client()
    try:
        service_account = client.get_service_account(
            service_account_name_or_id
        )
    except KeyError as err:
        cli_utils.error(str(err))
    else:
        cli_utils.print_pydantic_model(
            title=f"Service account '{service_account.name}'",
            model=service_account,
        )


@service_account.command("list")
@list_options(ServiceAccountFilter)
@click.pass_context
def list_service_accounts(ctx: click.Context, **kwargs: Any) -> None:
    """List all users.

    Args:
        ctx: The click context object
        kwargs: Keyword arguments to filter the list of users.
    """
    client = Client()
    with console.status("Listing service accounts...\n"):
        service_accounts = client.list_service_accounts(**kwargs)
        if not service_accounts:
            cli_utils.declare(
                "No service accounts found for the given filters."
            )
            return

        cli_utils.print_pydantic_models(
            service_accounts,
            exclude_columns=[
                "created",
                "updated",
            ],
        )


@service_account.command(
    "update",
    help="Update a service account.",
)
@click.argument("service_account_name_or_id", type=str, required=True)
@click.option(
    "--name",
    "-n",
    "updated_name",
    type=str,
    required=False,
    help="New service account name.",
)
@click.option(
    "--description",
    "-d",
    type=str,
    required=False,
    help="The API key description.",
)
@click.option(
    "--active",
    type=bool,
    required=False,
    help="Activate or deactivate a service account.",
)
def update_service_account(
    service_account_name_or_id: str,
    updated_name: Optional[str] = None,
    description: Optional[str] = None,
    active: Optional[bool] = None,
) -> None:
    """Update an existing service account.

    Args:
        service_account_name_or_id: The name or ID of the service account to
            update.
        updated_name: The new name of the service account.
        description: The new API key description.
        active: Activate or deactivate a service account.
    """
    try:
        Client().update_service_account(
            name_id_or_prefix=service_account_name_or_id,
            updated_name=updated_name,
            description=description,
            active=active,
        )
    except (KeyError, EntityExistsError) as err:
        cli_utils.error(str(err))


@service_account.command("delete")
@click.argument("service_account_name_or_id", type=str, required=True)
def delete_service_account(service_account_name_or_id: str) -> None:
    """Delete a service account.

    Args:
        service_account_name_or_id: The name or ID of the service account.
    """
    client = Client()
    try:
        client.delete_service_account(service_account_name_or_id)
    except (KeyError, IllegalOperationError) as err:
        cli_utils.error(str(err))

    cli_utils.declare(
        f"Deleted service account '{service_account_name_or_id}'."
    )


@service_account.group(
    cls=TagGroup,
    help="Commands for interacting with API keys.",
)
@click.pass_context
@click.argument("service_account_name_or_id", type=str, required=True)
def api_key(
    ctx: click.Context,
    service_account_name_or_id: str,
) -> None:
    """List and manage the API keys associated with a service account.

    Args:
        ctx: The click context.
        service_account_name_or_id: The name or ID of the service account.
    """
    ctx.obj = service_account_name_or_id


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
    "--set-key",
    is_flag=True,
    help="Configure the local client with the generated key.",
)
@click.pass_obj
def create_api_key(
    service_account_name_or_id: str,
    name: str,
    description: Optional[str],
    set_key: bool = False,
) -> None:
    """Create an API key.

    Args:
        service_account_name_or_id: The name or ID of the service account to
            which the API key should be added.
        name: Name of the API key
        description: The API key description.
        set_key: Configure the local client with the generated key.
    """
    _create_api_key(
        service_account_name_or_id=service_account_name_or_id,
        name=name,
        description=description,
        set_key=set_key,
    )


@api_key.command("describe", help="Describe an API key.")
@click.argument("name_or_id", type=str, required=True)
@click.pass_obj
def describe_api_key(service_account_name_or_id: str, name_or_id: str) -> None:
    """Describe an API key.

    Args:
        service_account_name_or_id: The name or ID of the service account to
            which the API key belongs.
        name_or_id: The name or ID of the API key to describe.
    """
    with console.status(f"Getting API key `{name_or_id}`...\n"):
        try:
            api_key = Client().get_api_key(
                service_account_name_id_or_prefix=service_account_name_or_id,
                name_id_or_prefix=name_or_id,
            )
        except KeyError as e:
            cli_utils.error(str(e))

        cli_utils.print_pydantic_model(
            title=f"API key '{api_key.name}'",
            model=api_key,
            exclude_columns={
                "key",
            },
        )


@api_key.command("list", help="List all API keys.")
@list_options(APIKeyFilter)
@click.pass_obj
def list_api_keys(service_account_name_or_id: str, **kwargs: Any) -> None:
    """List all API keys.

    Args:
        service_account_name_or_id: The name or ID of the service account for
            which to list the API keys.
        **kwargs: Keyword arguments to filter API keys.
    """
    with console.status("Listing API keys...\n"):
        try:
            api_keys = Client().list_api_keys(
                service_account_name_id_or_prefix=service_account_name_or_id,
                **kwargs,
            )
        except KeyError as e:
            cli_utils.error(str(e))

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
    help="Activate or deactivate an API key.",
)
@click.pass_obj
def update_api_key(
    service_account_name_or_id: str,
    name_or_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    active: Optional[bool] = None,
) -> None:
    """Update an API key.

    Args:
        service_account_name_or_id: The name or ID of the service account to
            which the API key belongs.
        name_or_id: The name or ID of the API key to update.
        name: The new name of the API key.
        description: The new description of the API key.
        active: Set an API key to active/inactive.
    """
    try:
        Client().update_api_key(
            service_account_name_id_or_prefix=service_account_name_or_id,
            name_id_or_prefix=name_or_id,
            name=name,
            description=description,
            active=active,
        )
    except (KeyError, EntityExistsError) as e:
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
    "--set-key",
    is_flag=True,
    help="Configure the local client with the generated key.",
)
@click.pass_obj
def rotate_api_key(
    service_account_name_or_id: str,
    name_or_id: str,
    retain: int = 0,
    set_key: bool = False,
) -> None:
    """Rotate an API key.

    Args:
        service_account_name_or_id: The name or ID of the service account to
            which the API key belongs.
        name_or_id: The name or ID of the API key to rotate.
        retain: Number of minutes for which the previous key is still valid
            after it has been rotated.
        set_key: Configure the local client with the newly generated key.
    """
    client = Client()
    zen_store = client.zen_store

    try:
        api_key = client.rotate_api_key(
            service_account_name_id_or_prefix=service_account_name_or_id,
            name_id_or_prefix=name_or_id,
            retain_period_minutes=retain,
        )
    except KeyError as e:
        cli_utils.error(str(e))

    cli_utils.declare(f"Successfully rotated API key `{name_or_id}`.")
    if retain:
        cli_utils.declare(
            f"The previous API key will remain valid for {retain} minutes."
        )

    if set_key and api_key.key:
        if zen_store.TYPE != StoreType.REST:
            cli_utils.warning(
                "Could not configure the local ZenML client with the generated "
                "API key. This type of authentication is only supported if "
                "connected to a ZenML server."
            )
        else:
            client.set_api_key(api_key.key)
            cli_utils.declare(
                "The local client has been configured with the new API key."
            )
            return

    cli_utils.declare(
        f"The new API key value is: '{api_key.key}'\nPlease store it "
        "safely as it will not be shown again.\nTo configure a ZenML "
        "client to use this API key, run:\n\n"
        f"zenml connect --url {zen_store.config.url} --api-key \\\n"
        f"    '{api_key.key}'\n"
    )


@api_key.command("delete")
@click.argument("name_or_id", type=str, required=True)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Don't ask for confirmation.",
)
@click.pass_obj
def delete_api_key(
    service_account_name_or_id: str, name_or_id: str, yes: bool = False
) -> None:
    """Delete an API key.

    Args:
        service_account_name_or_id: The name or ID of the service account to
            which the API key belongs.
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
        Client().delete_api_key(
            service_account_name_id_or_prefix=service_account_name_or_id,
            name_id_or_prefix=name_or_id,
        )
    except KeyError as e:
        cli_utils.error(str(e))
    else:
        cli_utils.declare(f"Deleted API key `{name_or_id}`.")
