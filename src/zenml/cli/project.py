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
"""Functionality to administer projects of the ZenML CLI and server."""

from typing import Optional

import click

from zenml.cli import utils as cli_utils
from zenml.cli.cli import TagGroup, cli
from zenml.cli.utils import warn_unsupported_non_default_project
from zenml.client import Client
from zenml.enums import CliCategories
from zenml.exceptions import EntityExistsError, IllegalOperationError


@cli.group(cls=TagGroup, tag=CliCategories.MANAGEMENT_TOOLS)
def project() -> None:
    """Commands for project management."""


@project.command("list", hidden=True)
def list_projects() -> None:
    """List all projects."""
    warn_unsupported_non_default_project()
    cli_utils.print_active_config()
    projects = Client().zen_store.list_projects()

    if projects:
        active_project = Client().active_project
        active_project_id = active_project.id if active_project else None
        cli_utils.print_pydantic_models(
            projects,
            exclude_columns=["id", "created", "updated"],
            is_active=(lambda p: p.id == active_project_id),
        )
    else:
        cli_utils.declare("No projects registered.")


@project.command("create", help="Create a new project.", hidden=True)
@click.argument("project_name", type=str, required=True)
@click.option("--description", "-d", type=str, required=False, default="")
def create_project(project_name: str, description: str) -> None:
    """Create a new project.

    Args:
        project_name: The name of the project.
        description: A description of the project.
    """
    warn_unsupported_non_default_project()
    cli_utils.print_active_config()
    try:
        Client().create_project(name=project_name, description=description)
    except EntityExistsError as err:
        cli_utils.error(str(err))
    cli_utils.declare(f"Created project '{project_name}'.")


@project.command("update", help="Update an existing project.", hidden=True)
@click.argument("project_name", type=str, required=True)
@click.option(
    "--name",
    "-n",
    "new_name",
    type=str,
    required=False,
    help="New project name.",
)
@click.option(
    "--description",
    "-d",
    "new_description",
    type=str,
    required=False,
    help="New project description.",
)
def update_project(
    project_name: str,
    new_name: Optional[str] = None,
    new_description: Optional[str] = None,
) -> None:
    """Update an existing project.

    Args:
        project_name: The name of the project.
        new_name: The new name of the project.
        new_description: The new description of the project.
    """
    warn_unsupported_non_default_project()
    cli_utils.print_active_config()
    try:
        Client().update_project(
            name_id_or_prefix=project_name,
            new_name=new_name,
            new_description=new_description,
        )
    except (EntityExistsError, KeyError, IllegalOperationError) as err:
        cli_utils.error(str(err))
    cli_utils.declare(f"Updated project '{project_name}'.")


@project.command("describe", hidden=True)
@click.argument("project_name_or_id", type=str, required=False)
def describe_project(project_name_or_id: Optional[str] = None) -> None:
    """Get the project.

    Args:
        project_name_or_id: The name or ID of the project to set as active.
    """
    warn_unsupported_non_default_project()
    client = Client()
    if not project_name_or_id:
        active_project = client.active_project
        cli_utils.print_pydantic_models(
            [active_project], exclude_columns=["created", "updated"]
        )
    else:
        try:
            project_ = client.get_project(project_name_or_id)
        except KeyError as err:
            cli_utils.error(str(err))
        else:
            cli_utils.print_pydantic_models(
                [project_], exclude_columns=["created", "updated"]
            )


@project.command("set", help="Set the active project.", hidden=True)
@click.argument("project_name_or_id", type=str, required=True)
def set_project(project_name_or_id: str) -> None:
    """Set the active project.

    Args:
        project_name_or_id: The name or ID of the project to set as active.
    """
    warn_unsupported_non_default_project()
    cli_utils.print_active_config()
    try:
        Client().set_active_project(project_name_or_id=project_name_or_id)
    except KeyError as err:
        cli_utils.error(str(err))
    cli_utils.declare(f"Set active project '{project_name_or_id}'.")


@project.command("delete", help="Delete a project.", hidden=True)
@click.argument("project_name_or_id", type=str, required=True)
def delete_project(project_name_or_id: str) -> None:
    """Delete a project.

    Args:
        project_name_or_id: Name or ID of project to delete.
    """
    warn_unsupported_non_default_project()
    cli_utils.print_active_config()
    confirmation = cli_utils.confirmation(
        f"Are you sure you want to delete project `{project_name_or_id}`? "
        "This will permanently delete all associated stacks, stack components, "
        "pipelines, runs, artifacts and metadata."
    )
    if not confirmation:
        cli_utils.declare("Project deletion canceled.")
        return
    try:
        Client().delete_project(project_name_or_id)
    except (KeyError, IllegalOperationError) as err:
        cli_utils.error(str(err))
    cli_utils.declare(f"Deleted project '{project_name_or_id}'.")
