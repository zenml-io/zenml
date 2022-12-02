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
"""Functionality to administer roles of the ZenML CLI and server."""

from typing import List, Optional, Tuple

import click

from zenml.cli import utils as cli_utils
from zenml.cli.cli import TagGroup, cli
from zenml.client import Client
from zenml.enums import CliCategories, PermissionType
from zenml.exceptions import EntityExistsError, IllegalOperationError


@cli.group(cls=TagGroup, tag=CliCategories.IDENTITY_AND_SECURITY)
def role() -> None:
    """Commands for role management."""


@role.command("list")
def list_roles() -> None:
    """List all roles."""
    cli_utils.print_active_config()
    roles = Client().list_roles()
    if not roles:
        cli_utils.declare("No roles registered.")
        return
    cli_utils.print_pydantic_models(
        roles,
        exclude_columns=["created", "updated"],
    )


@role.command("create", help="Create a new role.")
@click.argument("role_name", type=str, required=True)
@click.option(
    "--permissions",
    "-p",
    "permissions",
    type=click.Choice(choices=PermissionType.values()),
    multiple=True,
    help="Name of permission to attach to this role.",
)
def create_role(role_name: str, permissions: List[str]) -> None:
    """Create a new role.

    Args:
        role_name: Name of the role to create.
        permissions: Permissions to assign
    """
    cli_utils.print_active_config()

    try:
        Client().create_role(name=role_name, permissions_list=permissions)
        cli_utils.declare(f"Created role '{role_name}'.")
    except EntityExistsError as e:
        cli_utils.error(str(e))


@role.command("update", help="Update an existing role.")
@click.argument("role_name", type=str, required=True)
@click.option(
    "--name", "-n", "new_name", type=str, required=False, help="New role name."
)
@click.option(
    "--remove-permission",
    "-r",
    type=click.Choice(choices=PermissionType.values()),
    multiple=True,
    help="Name of permission to remove.",
)
@click.option(
    "--add-permission",
    "-a",
    type=click.Choice(choices=PermissionType.values()),
    multiple=True,
    help="Name of permission to add.",
)
def update_role(
    role_name: str,
    new_name: Optional[str] = None,
    remove_permission: Optional[List[str]] = None,
    add_permission: Optional[List[str]] = None,
) -> None:
    """Update an existing role.

    Args:
        role_name: The name of the role.
        new_name: The new name of the role.
        remove_permission: Name of permission to remove from role
        add_permission: Name of permission to add to role
    """
    cli_utils.print_active_config()

    try:
        Client().update_role(
            name_id_or_prefix=role_name,
            new_name=new_name,
            remove_permission=remove_permission,
            add_permission=add_permission,
        )
    except (
        EntityExistsError,
        KeyError,
        RuntimeError,
        IllegalOperationError,
    ) as err:
        cli_utils.error(str(err))
    cli_utils.declare(f"Updated role '{role_name}'.")


@role.command("delete", help="Delete a role.")
@click.argument("role_name_or_id", type=str, required=True)
def delete_role(role_name_or_id: str) -> None:
    """Delete a role.

    Args:
        role_name_or_id: Name or ID of the role to delete.
    """
    cli_utils.print_active_config()
    try:
        Client().delete_role(name_id_or_prefix=role_name_or_id)
    except (KeyError, IllegalOperationError) as err:
        cli_utils.error(str(err))
    cli_utils.declare(f"Deleted role '{role_name_or_id}'.")


@role.command("assign", help="Assign a role.")
@click.argument("role_name_or_id", type=str, required=True)
@click.option("--project", "project_name_or_id", type=str, required=False)
@click.option(
    "--user", "user_names_or_ids", type=str, required=False, multiple=True
)
@click.option(
    "--team", "team_names_or_ids", type=str, required=False, multiple=True
)
def assign_role(
    role_name_or_id: str,
    user_names_or_ids: Tuple[str],
    team_names_or_ids: Tuple[str],
    project_name_or_id: Optional[str] = None,
) -> None:
    """Assign a role.

    Args:
        role_name_or_id: Name or IDs of the role to assign.
        user_names_or_ids : Names or IDs of users to assign the role to.
        team_names_or_ids: Names or IDs of teams to assign the role to.
        project_name_or_id: Name or IDs of a project in which to assign the
            role. If this is not provided, the role will be assigned globally.
    """
    cli_utils.print_active_config()

    # Assign the role to users
    for user_name_or_id in user_names_or_ids:
        try:
            Client().create_role_assignment(
                role_name_or_id=role_name_or_id,
                user_or_team_name_or_id=user_name_or_id,
                is_user=True,
                project_name_or_id=project_name_or_id,
            )
        except KeyError as err:
            cli_utils.error(str(err))
        except EntityExistsError as err:
            cli_utils.error(str(err))
        else:
            cli_utils.declare(
                f"Assigned role '{role_name_or_id}' to user '{user_name_or_id}'."
            )

    # Assign the role to teams
    for team_name_or_id in team_names_or_ids:
        try:
            Client().create_role_assignment(
                role_name_or_id=role_name_or_id,
                user_or_team_name_or_id=team_name_or_id,
                is_user=False,
                project_name_or_id=project_name_or_id,
            )
        except KeyError as err:
            cli_utils.error(str(err))
        except EntityExistsError as err:
            cli_utils.warning(str(err))
        else:
            cli_utils.declare(
                f"Assigned role '{role_name_or_id}' to team '{team_name_or_id}'."
            )


@role.command("revoke", help="Revoke a role.")
@click.argument("role_name_or_id", type=str, required=True)
@click.option("--project", "project_name_or_id", type=str, required=False)
@click.option(
    "--user", "user_names_or_ids", type=str, required=False, multiple=True
)
@click.option(
    "--team", "team_names_or_ids", type=str, required=False, multiple=True
)
def revoke_role(
    role_name_or_id: str,
    user_names_or_ids: Tuple[str],
    team_names_or_ids: Tuple[str],
    project_name_or_id: Optional[str] = None,
) -> None:
    """Revoke a role.

    Args:
        role_name_or_id: Name or IDs of the role to revoke.
        user_names_or_ids: Names or IDs of users from which to revoke the role.
        team_names_or_ids: Names or IDs of teams from which to revoke the role.
        project_name_or_id: Name or IDs of a project in which to revoke the
            role. If this is not provided, the role will be revoked globally.
    """
    cli_utils.print_active_config()

    # Revoke the role from users
    for user_name_or_id in user_names_or_ids:
        try:
            Client().delete_role_assignment(
                role_name_or_id=role_name_or_id,
                user_or_team_name_or_id=user_name_or_id,
                is_user=True,
                project_name_or_id=project_name_or_id,
            )
        except KeyError as err:
            cli_utils.warning(str(err))
        else:
            cli_utils.declare(
                f"Revoked role '{role_name_or_id}' from user "
                f"'{user_name_or_id}'."
            )

    # Revoke the role from teams
    for team_name_or_id in team_names_or_ids:
        try:
            Client().delete_role_assignment(
                role_name_or_id=role_name_or_id,
                user_or_team_name_or_id=team_name_or_id,
                is_user=False,
                project_name_or_id=project_name_or_id,
            )
        except KeyError as err:
            cli_utils.warning(str(err))
        else:
            cli_utils.declare(
                f"Revoked role '{role_name_or_id}' from team "
                f"'{team_name_or_id}'."
            )


@role.group()
def assignment() -> None:
    """Commands for role management."""


@assignment.command("list")
@click.option("--role", "role_name_or_id", type=str, required=False)
@click.option("--project", "project_name_or_id", type=str, required=False)
@click.option(
    "--user",
    "user_name_or_id",
    type=str,
    required=False,
)
def list_role_assignments(
    role_name_or_id: Optional[str] = None,
    user_name_or_id: Optional[str] = None,
    project_name_or_id: Optional[str] = None,
) -> None:
    """List all role assignments.

    Args:
        role_name_or_id: Name or ID of a role to list role assignments for.
        user_name_or_id: Name or ID of a user to list role assignments for.
        project_name_or_id: Name or ID of a project to list role assignments
            for.
    """
    cli_utils.print_active_config()
    # Hacky workaround while role assignments are scoped to the user endpoint
    role_assignments = Client().list_role_assignment(
        role_name_or_id=role_name_or_id,
        user_name_or_id=user_name_or_id,
        project_name_or_id=project_name_or_id,
    )
    if not role_assignments:
        cli_utils.declare("No roles assigned.")
        return
    cli_utils.print_pydantic_models(
        role_assignments, exclude_columns=["id", "created", "updated"]
    )


@cli.group(cls=TagGroup, tag=CliCategories.IDENTITY_AND_SECURITY)
def permission() -> None:
    """Commands for role management."""


@permission.command("list")
def list_permissions() -> None:
    """List all role assignments."""
    cli_utils.print_active_config()
    permissions = [i.value for i in PermissionType]
    cli_utils.declare(
        f"The following permissions are currently supported: " f"{permissions}"
    )
