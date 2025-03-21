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
from zenml.config.global_config import GlobalConfiguration
from zenml.console import console
from zenml.enums import CliCategories, StoreType
from zenml.exceptions import (
    AuthorizationException,
    EntityExistsError,
    IllegalOperationError,
)
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
def list_users(ctx: click.Context, /, **kwargs: Any) -> None:
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
@click.option(
    "--is_admin",
    is_flag=True,
    help=(
        "Whether the user should be an admin. If not specified, the user will "
        "be a regular user."
    ),
    required=False,
    default=False,
)
def create_user(
    user_name: str,
    password: Optional[str] = None,
    is_admin: bool = False,
) -> None:
    """Create a new user.

    Args:
        user_name: The name of the user to create.
        password: The password of the user to create.
        is_admin: Whether the user should be an admin.
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
    else:
        cli_utils.warning(
            "Supplying password values in the command line is not safe. "
            "Please consider using the prompt option."
        )

    try:
        new_user = client.create_user(
            name=user_name, password=password, is_admin=is_admin
        )

        cli_utils.declare(f"Created user '{new_user.name}'.")
    except EntityExistsError as err:
        cli_utils.error(str(err))
    else:
        if not new_user.active and new_user.activation_token is not None:
            user_info = f"?user={str(new_user.id)}&username={new_user.name}&token={new_user.activation_token}"
            cli_utils.declare(
                f"The created user account is currently inactive. You can "
                f"activate it by visiting the dashboard at the following URL:\n"
                # TODO: keep only `activate-user` once legacy dashboard is gone
                f"{client.zen_store.url}/activate-user{user_info}\n\n"
                "If you are using Legacy dashboard visit the following URL:\n"
                f"{client.zen_store.url}/signup{user_info}\n"
            )


@user.command(
    "update",
    help="Update user information through the cli.",
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
@click.option(
    "--admin",
    "-a",
    "make_admin",
    is_flag=True,
    required=False,
    default=None,
    help="Whether the user should be an admin.",
)
@click.option(
    "--user",
    "-u",
    "make_user",
    is_flag=True,
    required=False,
    default=None,
    help="Whether the user should be a regular user.",
)
@click.option(
    "--active",
    "active",
    type=bool,
    required=False,
    default=None,
    help="Use to activate or deactivate a user account.",
)
def update_user(
    user_name_or_id: str,
    updated_name: Optional[str] = None,
    updated_full_name: Optional[str] = None,
    updated_email: Optional[str] = None,
    make_admin: Optional[bool] = None,
    make_user: Optional[bool] = None,
    active: Optional[bool] = None,
) -> None:
    """Update an existing user.

    Args:
        user_name_or_id: The name of the user to create.
        updated_name: The name of the user to create.
        updated_full_name: The name of the user to create.
        updated_email: The name of the user to create.
        make_admin: Whether the user should be an admin.
        make_user: Whether the user should be a regular user.
        active: Use to activate or deactivate a user account.
    """
    if make_admin is not None and make_user is not None:
        cli_utils.error(
            "Cannot set both --admin and --user flags as these are mutually exclusive."
        )
    try:
        current_user = Client().get_user(
            user_name_or_id, allow_name_prefix_match=False
        )
        if current_user.is_admin and make_user:
            confirmation = cli_utils.confirmation(
                f"Currently user `{current_user.name}` is an admin. Are you "
                "sure you want to make them a regular user?"
            )
            if not confirmation:
                cli_utils.declare("User update canceled.")
                return

        updated_is_admin = None
        if make_admin is True:
            updated_is_admin = True
        elif make_user is True:
            updated_is_admin = False
        Client().update_user(
            name_id_or_prefix=user_name_or_id,
            updated_name=updated_name,
            updated_full_name=updated_full_name,
            updated_email=updated_email,
            updated_is_admin=updated_is_admin,
            active=active,
        )
    except (KeyError, IllegalOperationError) as err:
        cli_utils.error(str(err))


@user.command(
    "change-password",
    help="Change the password for the current user account.",
)
@click.option(
    "--password",
    help=(
        "The new user password. If omitted, a prompt will be shown to enter "
        "the password."
    ),
    required=False,
    type=str,
)
@click.option(
    "--old-password",
    help=(
        "The old user password. If omitted, a prompt will be shown to enter "
        "the old password."
    ),
    required=False,
    type=str,
)
def change_user_password(
    password: Optional[str] = None, old_password: Optional[str] = None
) -> None:
    """Change the password of the current user.

    Args:
        password: The new password for the current user.
        old_password: The old password for the current user.
    """
    active_user = Client().active_user

    if old_password is not None or password is not None:
        cli_utils.warning(
            "Supplying password values in the command line is not safe. "
            "Please consider using the prompt option."
        )

    if old_password is None:
        old_password = click.prompt(
            f"Current password for user {active_user.name}",
            hide_input=True,
        )
    if password is None:
        password = click.prompt(
            f"New password for user {active_user.name}",
            hide_input=True,
        )
        password_again = click.prompt(
            f"Please re-enter the new password for user {active_user.name}",
            hide_input=True,
        )
        if password != password_again:
            cli_utils.error("Passwords do not match.")

    try:
        Client().update_user(
            name_id_or_prefix=active_user.id,
            old_password=old_password,
            updated_password=password,
        )
    except (KeyError, IllegalOperationError, AuthorizationException) as err:
        cli_utils.error(str(err))

    cli_utils.declare(
        f"Successfully updated password for active user '{active_user.name}'."
    )


@user.command(
    "deactivate",
    help="Generate an activation token to reset the password for a user account",
)
@click.argument("user_name_or_id", type=str, required=True)
def deactivate_user(
    user_name_or_id: str,
) -> None:
    """Reset the password of a user.

    Args:
        user_name_or_id: The name or ID of the user to reset the password for.
    """
    client = Client()

    store = GlobalConfiguration().store_configuration
    if store.type != StoreType.REST:
        cli_utils.error(
            "Deactivating users is only supported when connected to a ZenML "
            "server."
        )

    try:
        if not client.active_user.is_admin:
            cli_utils.error(
                "Only admins can reset the password of other users."
            )

        user = client.deactivate_user(
            name_id_or_prefix=user_name_or_id,
        )
    except (KeyError, IllegalOperationError) as err:
        cli_utils.error(str(err))

    user_info = f"?user={str(user.id)}&username={user.name}&token={user.activation_token}"
    cli_utils.declare(
        f"Successfully deactivated user account '{user.name}'."
        f"To reactivate the account, please visit the dashboard at the "
        "following URL:\n"
        # TODO: keep only `activate-user` once legacy dashboard is gone
        f"{client.zen_store.url}/activate-user{user_info}\n\n"
        "If you are using Legacy dashboard visit the following URL:\n"
        f"{client.zen_store.url}/signup{user_info}\n"
    )


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
