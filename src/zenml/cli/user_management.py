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
from zenml.enums import CliCategories
from zenml.exceptions import EntityExistsError, IllegalOperationError
from zenml.models import ProjectModel, RoleModel, TeamModel, UserModel
from zenml.repository import Repository
from zenml.utils.uuid_utils import parse_name_or_uuid


@cli.group(cls=TagGroup, tag=CliCategories.IDENTITY_AND_SECURITY)
def user() -> None:
    """Commands for user management."""


@user.command("get")
def get_user() -> None:
    """Get the active user."""
    cli_utils.print_active_config()
    cli_utils.declare(
        f"Active user: '{Repository().zen_store.active_user_name}'"
    )


@user.command("list")
def list_users() -> None:
    """List all users."""
    cli_utils.print_active_config()
    users = Repository().zen_store.users
    if not users:
        cli_utils.declare("No users registered.")
        return

    cli_utils.print_pydantic_models(
        users,
        is_active=lambda u: u.name == Repository().zen_store.active_user_name,
    )


@user.command("create", help="Create a new user.")
@click.argument("user_name", type=str, required=True)
# @click.option("--email", type=str, required=True)
# @click.password_option("--password", type=str, required=True)
def create_user(user_name: str) -> None:
    """Create a new user.

    Args:
        user_name: The name of the user to create.
    """
    cli_utils.print_active_config()
    try:
        Repository().zen_store.create_user(UserModel(name=user_name))
    except EntityExistsError as err:
        cli_utils.error(str(err))
    cli_utils.declare(f"Created user '{user_name}'.")


@user.command("delete")
@click.argument("user_name_or_id", type=str, required=True)
def delete_user(user_name_or_id: str) -> None:
    """Delete a user.

    Args:
        user_name_or_id: The name or ID of the user to delete.
    """
    cli_utils.print_active_config()
    try:
        Repository().delete_user(user_name_or_id)
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
    teams = Repository().zen_store.teams
    if not teams:
        cli_utils.declare("No teams registered.")
        return

    cli_utils.print_pydantic_models(teams)


@team.command("describe", help="List all users in a team.")
@click.argument("team_name_or_id", type=str, required=True)
def describe_team(team_name_or_id: str) -> None:
    """List all users in a team.

    Args:
        team_name_or_id: The name or ID of the team to describe.
    """
    cli_utils.print_active_config()
    try:
        users = Repository().zen_store.get_users_for_team(
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
        Repository().zen_store.create_team(TeamModel(name=team_name))
    except EntityExistsError as err:
        cli_utils.error(str(err))
    cli_utils.declare(f"Created team '{team_name}'.")


@team.command("delete", help="Delete a team.")
@click.argument("team_name_or_id", type=str, required=True)
def delete_team(team_name_or_id: str) -> None:
    """Delete a team.

    Args:
        team_name_or_id: The name or ID of the team to delete.
    """
    cli_utils.print_active_config()
    try:
        Repository().zen_store.delete_team(parse_name_or_uuid(team_name_or_id))
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
            Repository().zen_store.add_user_to_team(
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
            Repository().zen_store.remove_user_from_team(
                user_name_or_id=parse_name_or_uuid(user_name_or_id),
                team_name_or_id=parse_name_or_uuid(team_name_or_id),
            )
            cli_utils.declare(
                f"Removed user '{user_name_or_id}' from team '{team_name_or_id}'."
            )
    except KeyError as err:
        cli_utils.error(str(err))


@cli.group(cls=TagGroup, tag=CliCategories.MANAGEMENT_TOOLS)
def project() -> None:
    """Commands for project management."""


@project.command("list")
def list_projects() -> None:
    """List all projects."""
    cli_utils.print_active_config()
    projects = Repository().zen_store.list_projects()

    if projects:
        active_project = Repository().active_project
        active_project_id = active_project.id if active_project else None
        cli_utils.print_pydantic_models(
            projects,
            columns=("name", "description", "creation_date"),
            is_active=(lambda p: p.id == active_project_id),
        )
    else:
        cli_utils.declare("No projects registered.")


@project.command("create", help="Create a new project.")
@click.argument("project_name", type=str, required=True)
@click.option("--description", "-d", type=str, required=False)
def create_project(
    project_name: str, description: Optional[str] = None
) -> None:
    """Create a new project.

    Args:
        project_name: The name of the project.
        description: A description of the project.
    """
    cli_utils.print_active_config()
    try:
        Repository().zen_store.create_project(
            ProjectModel(name=project_name, description=description)
        )
    except EntityExistsError as err:
        cli_utils.error(str(err))
    cli_utils.declare(f"Created project '{project_name}'.")


@project.command("get")
def get_project() -> None:
    """Get the currently active project."""
    active_project = Repository().active_project
    if active_project:
        description = (
            "\nDescription: " + active_project.description
            if active_project.description
            else ""
        )
        cli_utils.declare(f"ACTIVE PROJECT: {active_project.name}{description}")
    else:
        cli_utils.warning(
            "No project is configured as active. Run "
            "`zenml project set <PROJECT_NAME>` to set an active project."
        )


@project.command("set", help="Set the active project.")
@click.argument("project_name_or_id", type=str, required=True)
def set_project(project_name_or_id: str) -> None:
    """Set the active project.

    Args:
        project_name_or_id: The name or ID of the project to set as active.
    """
    cli_utils.print_active_config()
    try:
        Repository().set_active_project(project_name_or_id=project_name_or_id)
    except KeyError as err:
        cli_utils.error(str(err))
    cli_utils.declare(f"Set active project '{project_name_or_id}'.")


@project.command("delete", help="Delete a project.")
@click.argument("project_name_or_id", type=str, required=True)
def delete_project(project_name_or_id: str) -> None:
    """Delete a project.

    Args:
        project_name_or_id: Name or ID of project to delete.
    """
    cli_utils.print_active_config()
    cli_utils.confirmation(
        f"Are you sure you want to delete project `{project_name_or_id}`? "
        "This will permanently delete all associated stacks, stack components, "
        "pipelines, runs, artifacts and metadata."
    )
    try:
        Repository().delete_project(project_name_or_id)
    except (KeyError, IllegalOperationError) as err:
        cli_utils.error(str(err))
    cli_utils.declare(f"Deleted project '{project_name_or_id}'.")


@cli.group(cls=TagGroup, tag=CliCategories.IDENTITY_AND_SECURITY)
def role() -> None:
    """Commands for role management."""


@role.command("list")
def list_roles() -> None:
    """List all roles."""
    cli_utils.print_active_config()
    roles = Repository().zen_store.roles
    if not roles:
        cli_utils.declare("No roles registered.")
        return
    cli_utils.print_pydantic_models(roles)


@role.command("create", help="Create a new role.")
@click.argument("role_name", type=str, required=True)
def create_role(role_name: str) -> None:
    """Create a new role.

    Args:
        role_name: Name of the role to create.
    """
    cli_utils.print_active_config()
    Repository().zen_store.create_role(role=RoleModel(name=role_name))
    cli_utils.declare(f"Created role '{role_name}'.")


@role.command("delete", help="Delete a role.")
@click.argument("role_name_or_id", type=str, required=True)
def delete_role(role_name_or_id: str) -> None:
    """Delete a role.

    Args:
        role_name_or_id: Name or ID of the role to delete.
    """
    cli_utils.print_active_config()
    try:
        Repository().zen_store.delete_role(
            role_name_or_id=parse_name_or_uuid(role_name_or_id)
        )
    except KeyError as err:
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
            Repository().zen_store.assign_role(
                role_name_or_id=role_name_or_id,
                user_or_team_name_or_id=user_name_or_id,
                is_user=True,
                project_name_or_id=project_name_or_id,
            )
        except KeyError as err:
            cli_utils.error(str(err))
        except EntityExistsError as err:
            cli_utils.warning(str(err))
        else:
            cli_utils.declare(
                f"Assigned role '{role_name_or_id}' to user '{user_name_or_id}'."
            )

    # Assign the role to teams
    for team_name_or_id in team_names_or_ids:
        try:
            Repository().zen_store.assign_role(
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
            Repository().zen_store.revoke_role(
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
            Repository().zen_store.revoke_role(
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
def list_role_assignments() -> None:
    """List all role assignments."""
    cli_utils.print_active_config()
    role_assignments = Repository().zen_store.role_assignments
    if not role_assignments:
        cli_utils.declare("No roles assigned.")
        return
    cli_utils.print_pydantic_models(role_assignments)
