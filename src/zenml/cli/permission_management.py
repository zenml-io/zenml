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
from pydantic import BaseModel

from zenml.cli import utils as cli_utils
from zenml.cli.cli import cli
from zenml.repository import Repository


def _convert_to_table_dict(model: BaseModel):
    return {key.upper(): str(value) for key, value in model.dict().items()}


@cli.group()
def user() -> None:
    """Commands for user management."""


@user.command("list")
def list_users():
    """List all users."""
    cli_utils.print_active_profile()
    user_dicts = [
        _convert_to_table_dict(user_)
        for user_ in Repository().stack_store.users
    ]
    cli_utils.print_table(user_dicts)


@user.command("create")
@click.argument("user_name", type=str, required=True)
# @click.option("--email", type=str, required=True)
# @click.password_option("--password", type=str, required=True)
def create_user(user_name: str):
    """Create a new user."""
    cli_utils.print_active_profile()
    Repository().stack_store.create_user(user_name=user_name)


@user.command("delete")
@click.argument("user_name", type=str, required=True)
def delete_user(user_name: str):
    """Delete a user."""
    cli_utils.print_active_profile()
    Repository().stack_store.delete_user(user_name=user_name)


@cli.group()
def team() -> None:
    """Commands for team management."""


@team.command("list")
def list_teams():
    """List all teams."""
    cli_utils.print_active_profile()
    team_dicts = [
        _convert_to_table_dict(team_)
        for team_ in Repository().stack_store.teams
    ]
    cli_utils.print_table(team_dicts)


@team.command("create")
@click.argument("team_name", type=str, required=True)
def create_team(team_name: str):
    """Create a new team."""
    cli_utils.print_active_profile()
    Repository().stack_store.create_team(team_name=team_name)


@team.command("delete")
@click.argument("team_name", type=str, required=True)
def delete_team(team_name: str):
    """Delete a team."""
    cli_utils.print_active_profile()
    Repository().stack_store.delete_team(team_name=team_name)


@team.command("add")
@click.argument("team_name", type=str, required=True)
@click.option("--user", "user_names", type=str, required=True, multiple=True)
def add_users(team_name: str, user_names: Tuple[str]):
    """Add users to a team."""
    cli_utils.print_active_profile()
    for user_name in user_names:
        Repository().stack_store.add_user_to_team(
            team_name=team_name, user_name=user_name
        )


@team.command("remove")
@click.argument("team_name", type=str, required=True)
@click.option("--user", "user_names", type=str, required=True, multiple=True)
def remove_users(team_name: str, user_names: Tuple[str]):
    """Remove users from a team."""
    cli_utils.print_active_profile()
    for user_name in user_names:
        Repository().stack_store.remove_user_from_team(
            team_name=team_name, user_name=user_name
        )


@cli.group()
def project() -> None:
    """Commands for project management."""


@project.command("list")
def list_projects():
    """List all projects."""
    cli_utils.print_active_profile()
    project_dicts = [
        _convert_to_table_dict(project_)
        for project_ in Repository().stack_store.projects
    ]
    cli_utils.print_table(project_dicts)


@project.command("create")
@click.argument("project_name", type=str, required=True)
@click.option(
    "--description",
    type=str,
    required=False,
)
def create_project(project_name: str, description: Optional[str] = None):
    """Create a new project."""
    cli_utils.print_active_profile()
    Repository().stack_store.create_project(
        project_name=project_name, description=description
    )


@project.command("delete")
@click.argument("project_name", type=str, required=True)
def delete_project(project_name: str):
    """Delete a project."""
    cli_utils.print_active_profile()
    Repository().stack_store.delete_project(project_name=project_name)


@cli.group()
def role() -> None:
    """Commands for role management."""


@role.command("list")
def list_roles():
    """List all roles."""
    cli_utils.print_active_profile()
    role_dicts = [
        _convert_to_table_dict(role_)
        for role_ in Repository().stack_store.roles
    ]
    cli_utils.print_table(role_dicts)


@role.command("create")
@click.argument("role_name", type=str, required=True)
def create_role(role_name: str):
    """Create a new role."""
    cli_utils.print_active_profile()
    Repository().stack_store.create_role(role_name=role_name)


@role.command("delete")
@click.argument("role_name", type=str, required=True)
def delete_role(role_name: str):
    """Delete a role."""
    cli_utils.print_active_profile()
    Repository().stack_store.delete_role(role_name=role_name)


@role.command("assign")
@click.argument("role_name", type=str, required=True)
@click.option("--project", "project_name", type=str, required=True)
@click.option("--user", "user_names", type=str, required=False, multiple=True)
@click.option("--team", "team_names", type=str, required=False, multiple=True)
def assign_role(
    role_name: str,
    project_name: str,
    user_names: Tuple[str],
    team_names: Tuple[str],
):
    """Assign a role."""
    cli_utils.print_active_profile()
    for user_name in user_names:
        Repository().stack_store.assign_role(
            role_name=role_name,
            project_name=project_name,
            entity_name=user_name,
            is_user=True,
        )

    for team_name in team_names:
        Repository().stack_store.assign_role(
            role_name=role_name,
            project_name=project_name,
            entity_name=team_name,
            is_user=False,
        )


@role.command("revoke")
@click.argument("role_name", type=str, required=True)
@click.option("--project", "project_name", type=str, required=True)
@click.option("--user", "user_names", type=str, required=False, multiple=True)
@click.option("--team", "team_names", type=str, required=False, multiple=True)
def revoke_role(
    role_name: str,
    project_name: str,
    user_names: Tuple[str],
    team_names: Tuple[str],
):
    """Revoke a role."""
    cli_utils.print_active_profile()
    for user_name in user_names:
        Repository().stack_store.revoke_role(
            role_name=role_name,
            project_name=project_name,
            entity_name=user_name,
            is_user=True,
        )

    for team_name in team_names:
        Repository().stack_store.revoke_role(
            role_name=role_name,
            project_name=project_name,
            entity_name=team_name,
            is_user=False,
        )


@role.group()
def assignment() -> None:
    """Commands for role management."""


@assignment.command("list")
def list_role_assignments():
    """List all role assignments."""
    cli_utils.print_active_profile()
    role_assignment_dicts = [
        _convert_to_table_dict(role_assignment)
        for role_assignment in Repository().stack_store.role_assignments
    ]
    cli_utils.print_table(role_assignment_dicts)
