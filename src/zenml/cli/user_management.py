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
"""Functionality to administer users of the ZenML CLI and server."""

from typing import Any, Optional

import click

from zenml.cli import utils as cli_utils
from zenml.cli.cli import TagGroup, cli
from zenml.cli.utils import is_sorted_or_filtered, list_options
from zenml.client import Client
from zenml.console import console
from zenml.enums import CliCategories, StoreType
from zenml.exceptions import EntityExistsError, IllegalOperationError
from zenml.models import UserFilter


@cli.group(cls=TagGroup, tag=CliCategories.IDENTITY_AND_SECURITY)
def user() -> None:
    """Commands for user management."""


@user.command("describe")
@click.argument("user_name_or_id", type=str, required=False)
def describe_user(user_name_or_id: Optional[str] = None) -> None:
    """Get the user.

    Args:
        user_name_or_id: The name or ID of the user.
    """
    client = Client()
    if not user_name_or_id:
        active_user = client.active_user
        cli_utils.print_pydantic_models(
            [active_user],
            exclude_columns=[
                "created",
                "updated",
                "email",
                "email_opted_in",
                "activation_token",
            ],
        )
    else:
        try:
            user = client.get_user(user_name_or_id)
        except KeyError as err:
            cli_utils.error(str(err))
        else:
            cli_utils.print_pydantic_models(
                [user],
                exclude_columns=[
                    "created",
                    "updated",
                    "email",
                    "email_opted_in",
                    "activation_token",
                ],
            )


@user.command("list")
@list_options(UserFilter)
@click.pass_context
def list_users(ctx: click.Context, **kwargs: Any) -> None:
    """List all users.

    Args:
        ctx: The click context object
        kwargs: Keyword arguments to filter the list of users.
    """
    client = Client()
    with console.status("Listing stacks...\n"):
        users = client.list_users(**kwargs)
        if not users:
            cli_utils.declare("No users found for the given filters.")
            return

        cli_utils.print_pydantic_models(
            users,
            exclude_columns=[
                "created",
                "updated",
                "email",
                "email_opted_in",
                "activation_token",
            ],
            active_models=[Client().active_user],
            show_active=not is_sorted_or_filtered(ctx),
        )


@user.command(
    "create",
    help="Create a new user. If an empty password is configured, an activation "
    "token is generated and a link to the dashboard is provided where the "
    "user can activate the account.",
)
@click.argument("user_name", type=str, required=True)
@click.option(
    "--password",
    help=(
        "The user password. If omitted, a prompt will be shown to enter the "
        "password. If an empty password is entered, an activation token is "
        "generated and a link to the dashboard is provided where the user can "
        "activate the account."
    ),
    required=False,
    type=str,
)
def create_user(
    user_name: str,
    password: Optional[str] = None,
) -> None:
    """Create a new user.

    Args:
        user_name: The name of the user to create.
        password: The password of the user to create.
    """
    client = Client()
    if not password:
        if client.zen_store.type != StoreType.REST:
            password = click.prompt(
                f"Password for user {user_name}",
                hide_input=True,
            )
        else:
            password = click.prompt(
                f"Password for user {user_name}. Leave empty to generate an "
                f"activation token",
                default="",
                hide_input=True,
            )

    try:
        new_user = client.create_user(name=user_name, password=password)

        cli_utils.declare(f"Created user '{new_user.name}'.")
    except EntityExistsError as err:
        cli_utils.error(str(err))
    else:
        if not new_user.active and new_user.activation_token is not None:
            cli_utils.declare(
                f"The created user account is currently inactive. You can "
                f"activate it by visiting the dashboard at the following URL:\n"
                f"{client.zen_store.url}/signup?user={str(new_user.id)}&username={new_user.name}&token={new_user.activation_token}\n"
            )


@user.command(
    "update",
    help="Update user information through the cli. All attributes "
    "except for password can be updated through the cli.",
)
@click.argument("user_name_or_id", type=str, required=True)
@click.option(
    "--name",
    "-n",
    "updated_name",
    type=str,
    required=False,
    help="New user name.",
)
@click.option(
    "--full_name",
    "-f",
    "updated_full_name",
    type=str,
    required=False,
    help="New full name. If this contains an empty space make sure to surround "
    "the name with quotes '<Full Name>'.",
)
@click.option(
    "--email",
    "-e",
    "updated_email",
    type=str,
    required=False,
    help="New user email.",
)
def update_user(
    user_name_or_id: str,
    updated_name: Optional[str] = None,
    updated_full_name: Optional[str] = None,
    updated_email: Optional[str] = None,
) -> None:
    """Create a new user.

    Args:
        user_name_or_id: The name of the user to create.
        updated_name: The name of the user to create.
        updated_full_name: The name of the user to create.
        updated_email: The name of the user to create.
    """
    try:
        Client().update_user(
            name_id_or_prefix=user_name_or_id,
            updated_name=updated_name,
            updated_full_name=updated_full_name,
            updated_email=updated_email,
        )
    except (KeyError, IllegalOperationError) as err:
        cli_utils.error(str(err))


@user.command("delete")
@click.argument("user_name_or_id", type=str, required=True)
def delete_user(user_name_or_id: str) -> None:
    """Delete a user.

    Args:
        user_name_or_id: The name or ID of the user to delete.
    """
    try:
        Client().delete_user(user_name_or_id)
    except (KeyError, IllegalOperationError) as err:
        cli_utils.error(str(err))
    cli_utils.declare(f"Deleted user '{user_name_or_id}'.")
