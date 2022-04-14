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

from typing import Optional, Tuple

import click

from zenml.cli import utils as cli_utils
from zenml.cli.cli import cli
from zenml.repository import Repository


@cli.group()
def user() -> None:
    """Commands for user management."""


@user.command("get")
def get_user() -> None:
    """Get the active user."""
    cli_utils.print_active_profile()
    cli_utils.declare(f"Active user: '{Repository().active_user_name}'")


@user.command("set")
@click.argument("user_name", type=str)
def set_user(user_name: str) -> None:
    """Set the active user."""
    cli_utils.print_active_profile()
    repo = Repository()
    try:
        repo.zen_store.get_user(user_name)
    except KeyError:
        cli_utils.error(f"No user with name {user_name}.")

    Repository().active_profile.activate_user(user_name)
    cli_utils.declare(f"Active user: '{Repository().active_user_name}'")


@user.command("list")
def list_users() -> None:
    """List all users."""
    cli_utils.print_active_profile()
    users = Repository().zen_store.users
    if not users:
        cli_utils.declare("No users registered.")
        return

    cli_utils.print_pydantic_models(users)


@user.command("create")
@click.argument("user_name", type=str, required=True)
# @click.option("--email", type=str, required=True)
# @click.password_option("--password", type=str, required=True)
def create_user(user_name: str) -> None:
    """Create a new user."""
    cli_utils.print_active_profile()
    Repository().zen_store.create_user(user_name=user_name)


@user.command("delete")
@click.argument("user_name", type=str, required=True)
def delete_user(user_name: str) -> None:
    """Delete a user."""
    cli_utils.print_active_profile()
    try:
        Repository().zen_store.delete_user(user_name=user_name)
    except KeyError:
        cli_utils.warning(f"No user found for name '{user_name}'.")


@cli.group()
def team() -> None:
    """Commands for team management."""


@team.command("list")
def list_teams() -> None:
    """List all teams."""
    cli_utils.print_active_profile()
    teams = Repository().zen_store.teams
    if not teams:
        cli_utils.declare("No teams registered.")
        return

    cli_utils.print_pydantic_models(teams)


@team.command("describe")
@click.argument("team_name", type=str, required=True)
def describe_team(team_name: str) -> None:
    """Print details of a team."""
    cli_utils.print_active_profile()
    try:
        users = Repository().zen_store.get_users_for_team(team_name=team_name)
    except KeyError:
        cli_utils.warning(f"No team found for name '{team_name}'.")
    else:
        cli_utils.declare(
            f"TEAM: {team_name}, USERS: {set(user_.name for user_ in users)}"
        )


@team.command("create")
@click.argument("team_name", type=str, required=True)
def create_team(team_name: str) -> None:
    """Create a new team."""
    cli_utils.print_active_profile()
    Repository().zen_store.create_team(team_name=team_name)


@team.command("delete")
@click.argument("team_name", type=str, required=True)
def delete_team(team_name: str) -> None:
    """Delete a team."""
    cli_utils.print_active_profile()
    try:
        Repository().zen_store.delete_team(team_name=team_name)
    except KeyError:
        cli_utils.warning(f"No team found for name '{team_name}'.")


@team.command("add")
@click.argument("team_name", type=str, required=True)
@click.option("--user", "user_names", type=str, required=True, multiple=True)
def add_users(team_name: str, user_names: Tuple[str]) -> None:
    """Add users to a team."""
    cli_utils.print_active_profile()
    for user_name in user_names:
        cli_utils.declare(f"Adding user '{user_name}' to team '{team_name}'.")
        try:
            Repository().zen_store.add_user_to_team(
                team_name=team_name, user_name=user_name
            )
        except KeyError:
            cli_utils.warning(
                "Failed to add user. Either the user or the team doesn't exist."
            )


@team.command("remove")
@click.argument("team_name", type=str, required=True)
@click.option("--user", "user_names", type=str, required=True, multiple=True)
def remove_users(team_name: str, user_names: Tuple[str]) -> None:
    """Remove users from a team."""
    cli_utils.print_active_profile()
    for user_name in user_names:
        cli_utils.declare(
            f"Removing user '{user_name}' from team '{team_name}'."
        )
        try:
            Repository().zen_store.remove_user_from_team(
                team_name=team_name, user_name=user_name
            )
        except KeyError:
            cli_utils.warning(
                "Failed to remove user. Either the user or the team doesn't "
                "exist."
            )


@cli.group()
def project() -> None:
    """Commands for project management."""


@project.command("list")
def list_projects() -> None:
    """List all projects."""
    cli_utils.print_active_profile()
    projects = Repository().zen_store.projects
    if not projects:
        cli_utils.declare("No projects registered.")
        return

    cli_utils.print_pydantic_models(projects)


@project.command("create")
@click.argument("project_name", type=str, required=True)
@click.option(
    "--description",
    type=str,
    required=False,
)
def create_project(
    project_name: str, description: Optional[str] = None
) -> None:
    """Create a new project."""
    cli_utils.print_active_profile()
    Repository().zen_store.create_project(
        project_name=project_name, description=description
    )


@project.command("delete")
@click.argument("project_name", type=str, required=True)
def delete_project(project_name: str) -> None:
    """Delete a project."""
    cli_utils.print_active_profile()
    try:
        Repository().zen_store.delete_project(project_name=project_name)
    except KeyError:
        cli_utils.warning(f"No project found for name '{project_name}'.")


@cli.group()
def role() -> None:
    """Commands for role management."""


@role.command("list")
def list_roles() -> None:
    """List all roles."""
    cli_utils.print_active_profile()
    roles = Repository().zen_store.roles
    if not roles:
        cli_utils.declare("No roles registered.")
        return

    cli_utils.print_pydantic_models(roles)


@role.command("create")
@click.argument("role_name", type=str, required=True)
def create_role(role_name: str) -> None:
    """Create a new role."""
    cli_utils.print_active_profile()
    Repository().zen_store.create_role(role_name=role_name)


@role.command("delete")
@click.argument("role_name", type=str, required=True)
def delete_role(role_name: str) -> None:
    """Delete a role."""
    cli_utils.print_active_profile()
    try:
        Repository().zen_store.delete_role(role_name=role_name)
    except KeyError:
        cli_utils.warning(f"No role found for name '{role_name}'.")


@role.command("assign")
@click.argument("role_name", type=str, required=True)
@click.option("--user", "user_names", type=str, required=False, multiple=True)
@click.option("--team", "team_names", type=str, required=False, multiple=True)
@click.option("--project", "project_name", type=str, required=False)
def assign_role(
    role_name: str,
    user_names: Tuple[str],
    team_names: Tuple[str],
    project_name: Optional[str] = None,
) -> None:
    """Assign a role."""
    cli_utils.print_active_profile()
    for user_name in user_names:
        cli_utils.declare(
            f"Assigning role '{role_name}' to user '{user_name}'."
        )
        try:
            Repository().zen_store.assign_role(
                role_name=role_name,
                project_name=project_name,
                entity_name=user_name,
                is_user=True,
            )
        except KeyError:
            cli_utils.warning(
                "Failed to assign role. Either the role, user or project "
                "doesn't exist."
            )

    for team_name in team_names:
        cli_utils.declare(
            f"Assigning role '{role_name}' to team '{team_name}'."
        )
        try:
            Repository().zen_store.assign_role(
                role_name=role_name,
                project_name=project_name,
                entity_name=team_name,
                is_user=False,
            )
        except KeyError:
            cli_utils.warning(
                "Failed to assign role. Either the role, team or project "
                "doesn't exist."
            )


@role.command("revoke")
@click.argument("role_name", type=str, required=True)
@click.option("--user", "user_names", type=str, required=False, multiple=True)
@click.option("--team", "team_names", type=str, required=False, multiple=True)
@click.option("--project", "project_name", type=str, required=False)
def revoke_role(
    role_name: str,
    user_names: Tuple[str],
    team_names: Tuple[str],
    project_name: Optional[str] = None,
) -> None:
    """Revoke a role."""
    cli_utils.print_active_profile()
    for user_name in user_names:
        cli_utils.declare(
            f"Revoking role '{role_name}' from user '{user_name}'."
        )
        try:
            Repository().zen_store.revoke_role(
                role_name=role_name,
                project_name=project_name,
                entity_name=user_name,
                is_user=True,
            )
        except KeyError:
            cli_utils.warning(
                "Failed to revoke role. Either the role, user or project "
                "doesn't exist."
            )

    for team_name in team_names:
        cli_utils.declare(
            f"Revoking role '{role_name}' from team '{team_name}'."
        )

        try:
            Repository().zen_store.revoke_role(
                role_name=role_name,
                project_name=project_name,
                entity_name=team_name,
                is_user=False,
            )
        except KeyError:
            cli_utils.warning(
                "Failed to revoke role. Either the role, team or project "
                "doesn't exist."
            )


@role.group()
def assignment() -> None:
    """Commands for role management."""


@assignment.command("list")
def list_role_assignments() -> None:
    """List all role assignments."""
    cli_utils.print_active_profile()
    role_assignments = Repository().zen_store.role_assignments
    if not role_assignments:
        cli_utils.declare("No roles assigned.")
        return

    cli_utils.print_pydantic_models(role_assignments)
