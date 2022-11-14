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

from typing import Optional, Tuple

import click

from zenml.cli import utils as cli_utils
from zenml.cli.cli import TagGroup, cli
from zenml.client import Client
from zenml.enums import CliCategories, StoreType
from zenml.exceptions import EntityExistsError, IllegalOperationError
from zenml.utils.uuid_utils import parse_name_or_uuid


@cli.group(cls=TagGroup, tag=CliCategories.IDENTITY_AND_SECURITY)
def user() -> None:
    """Commands for user management."""


@user.command("describe")
@click.argument("user_name_or_id", type=str, required=False)
def describe_user(user_name_or_id: Optional[str] = None) -> None:
    """Get the user.

    Args:
        user_name_or_id: The name or ID of the user."""
    cli_utils.print_active_config()
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
        user = client.get_user(user_name_or_id)
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
def list_users() -> None:
    """List all users."""
    cli_utils.print_active_config()
    users = Client().zen_store.users
    if not users:
        cli_utils.declare("No users registered.")
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
        is_active=lambda u: u.name == Client().zen_store.active_user_name,
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
    "--role",
    "-r",
    "initial_role",
    help=("Give the user an initial role."),
    required=False,
    type=str,
    default="admin",
)
def create_user(
    user_name: str,
    initial_role: str = "admin",
    password: Optional[str] = None,
) -> None:
    """Create a new user.

    Args:
        user_name: The name of the user to create.
        password: The password of the user to create.
        initial_role: Give the user an initial role
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

    cli_utils.print_active_config()

    try:
        new_user = client.create_user(name=user_name, password=password)

        cli_utils.declare(f"Created user '{new_user.name}'.")
    except EntityExistsError as err:
        cli_utils.error(str(err))
    else:
        try:
            client.create_role_assignment(
                role_name_or_id=initial_role,
                user_or_team_name_or_id=str(new_user.id),
                project_name_or_id=None,
                is_user=True
            )
        except KeyError as err:
            cli_utils.error(str(err))

        if not new_user.active and new_user.activation_token is not None:
            cli_utils.declare(
                f"The created user account is currently inactive. You can "
                f"activate it by visiting the dashboard at the following URL:\n"
                f"{client.zen_store.url}/signup?user={str(new_user.id)}&username={new_user.name}&token={new_user.activation_token.get_secret_value()}\n"
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
            user_name_or_id=user_name_or_id,
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
    cli_utils.print_active_config()
    try:
        Client().delete_user(user_name_or_id)
    except (KeyError, IllegalOperationError) as err:
        cli_utils.error(str(err))
    cli_utils.declare(f"Deleted user '{user_name_or_id}'.")


@cli.group(cls=TagGroup, tag=CliCategories.IDENTITY_AND_SECURITY)
def team() -> None:
    """Commands for team management."""


@team.command("list")
def list_teams() -> None:
    """List all teams."""
    cli_utils.print_active_config()
    teams = Client().zen_store.teams
    if not teams:
        cli_utils.declare("No teams registered.")
        return

    cli_utils.print_pydantic_models(
        teams,
        exclude_columns=["id", "created", "updated"],
    )


@team.command("describe", help="List all users in a team.")
@click.argument("team_name_or_id", type=str, required=True)
def describe_team(team_name_or_id: str) -> None:
    """List all users in a team.

    Args:
        team_name_or_id: The name or ID of the team to describe.
    """
    cli_utils.print_active_config()
    try:
        users = Client().zen_store.get_users_for_team(
            team_name_or_id=parse_name_or_uuid(team_name_or_id)
        )
    except KeyError as err:
        cli_utils.error(str(err))
    if not users:
        cli_utils.declare(f"Team '{team_name_or_id}' has no users.")
        return
    user_names = set([user.name for user in users])
    cli_utils.declare(
        f"Team '{team_name_or_id}' has the following users: {user_names}"
    )


@team.command("create", help="Create a new team.")
@click.argument("team_name", type=str, required=True)
def create_team(team_name: str) -> None:
    """Create a new team.

    Args:
        team_name: Name of the team to create.
    """
    cli_utils.print_active_config()
    try:
        from zenml.models import TeamModel

        Client().zen_store.create_team(TeamModel(name=team_name))
    except EntityExistsError as err:
        cli_utils.error(str(err))
    cli_utils.declare(f"Created team '{team_name}'.")


@team.command("update", help="Update an existing team.")
@click.argument("team_name", type=str, required=True)
@click.option("--name", "-n", type=str, required=False, help="New team name.")
def update_team(
    team_name: str,
    name: Optional[str] = None,
) -> None:
    """Update an existing team.

    Args:
        team_name: The name of the team.
        name: The new name of the team.
    """
    cli_utils.print_active_config()
    try:
        team = Client().zen_store.get_team(team_name)
        team.name = name or team.name
        Client().zen_store.update_team(team)
    except (EntityExistsError, KeyError) as err:
        cli_utils.error(str(err))
    cli_utils.declare(f"Updated team '{team_name}'.")


@team.command("delete", help="Delete a team.")
@click.argument("team_name_or_id", type=str, required=True)
def delete_team(team_name_or_id: str) -> None:
    """Delete a team.

    Args:
        team_name_or_id: The name or ID of the team to delete.
    """
    cli_utils.print_active_config()
    try:
        Client().zen_store.delete_team(parse_name_or_uuid(team_name_or_id))
    except KeyError as err:
        cli_utils.error(str(err))
    cli_utils.declare(f"Deleted team '{team_name_or_id}'.")


@team.command("add", help="Add users to a team.")
@click.argument("team_name_or_id", type=str, required=True)
@click.option(
    "--user", "user_names_or_ids", type=str, required=True, multiple=True
)
def add_users(team_name_or_id: str, user_names_or_ids: Tuple[str]) -> None:
    """Add users to a team.

    Args:
        team_name_or_id: Name or ID of the team.
        user_names_or_ids: The names or IDs of the users to add to the team.
    """
    cli_utils.print_active_config()

    try:
        for user_name_or_id in user_names_or_ids:
            Client().zen_store.add_user_to_team(
                user_name_or_id=parse_name_or_uuid(user_name_or_id),
                team_name_or_id=parse_name_or_uuid(team_name_or_id),
            )
            cli_utils.declare(
                f"Added user '{user_name_or_id}' to team '{team_name_or_id}'."
            )
    except (KeyError, EntityExistsError) as err:
        cli_utils.error(str(err))


@team.command("remove", help="Remove users from a team.")
@click.argument("team_name_or_id", type=str, required=True)
@click.option(
    "--user", "user_names_or_ids", type=str, required=True, multiple=True
)
def remove_users(team_name_or_id: str, user_names_or_ids: Tuple[str]) -> None:
    """Remove users from a team.

    Args:
        team_name_or_id: Name or ID of the team.
        user_names_or_ids: Names or IDS of the users.
    """
    cli_utils.print_active_config()

    try:
        for user_name_or_id in user_names_or_ids:
            Client().zen_store.remove_user_from_team(
                user_name_or_id=parse_name_or_uuid(user_name_or_id),
                team_name_or_id=parse_name_or_uuid(team_name_or_id),
            )
            cli_utils.declare(
                f"Removed user '{user_name_or_id}' from team '{team_name_or_id}'."
            )
    except KeyError as err:
        cli_utils.error(str(err))
