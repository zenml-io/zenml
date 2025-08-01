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

from typing import Any, Dict, Optional

import click

from zenml.cli import utils as cli_utils
from zenml.cli.cli import TagGroup, cli
from zenml.cli.utils import (
    check_zenml_pro_project_availability,
    enhanced_list_options,
    format_date_for_table,
    is_sorted_or_filtered,
    prepare_list_data,
)
from zenml.client import Client
from zenml.console import console
from zenml.enums import CliCategories
from zenml.models import ProjectFilter


def _project_to_print(project: Any) -> Dict[str, Any]:
    """Convert a project response to a dictionary suitable for table display.

    Args:
        project: Project response object

    Returns:
        Dictionary containing formatted project data for table display
    """
    return {
        "name": project.name,
        "description": project.description or "",
        "created": format_date_for_table(project.created),
    }


@cli.group(cls=TagGroup, tag=CliCategories.MANAGEMENT_TOOLS)
def project() -> None:
    """Commands for project management."""


@project.command("list")
@enhanced_list_options(ProjectFilter)
@click.pass_context
def list_projects(ctx: click.Context, /, **kwargs: Any) -> None:
    """List all projects.

    Args:
        ctx: The click context object
        **kwargs: Keyword arguments to filter the list of projects.
    """
    check_zenml_pro_project_availability()

    # Extract table options from kwargs
    table_kwargs = cli_utils.extract_table_options(kwargs)

    client = Client()
    with console.status("Listing projects..."):
        projects = client.list_projects(**kwargs)
        if projects:
            try:
                active_project = [client.active_project]
            except Exception:
                active_project = []

            # Prepare data based on output format
            output_format = (
                table_kwargs.get("output")
                or cli_utils.get_default_output_format()
            )

            # Handle both paginated and non-paginated responses
            project_list = (
                projects.items if hasattr(projects, "items") else projects
            )

            # Use centralized data preparation
            project_data = prepare_list_data(
                project_list, output_format, _project_to_print
            )

            # Handle table output with enhanced system
            cli_utils.handle_table_output(
                data=project_data,
                page=projects,
                active_models=active_project,
                show_active=not is_sorted_or_filtered(ctx),
                **table_kwargs,
            )
        else:
            cli_utils.declare("No projects found.")


@project.command("register")
@click.option(
    "--set",
    "set_project",
    is_flag=True,
    help="Immediately set this project as active.",
    type=click.BOOL,
)
@click.option(
    "--display-name",
    "display_name",
    type=str,
    required=False,
    help="The display name of the project.",
)
@click.option(
    "--set-default",
    "set_default",
    is_flag=True,
    help="Set this project as the default project.",
)
@click.argument("project_name", type=str, required=True)
def register_project(
    project_name: str,
    set_project: bool = False,
    display_name: Optional[str] = None,
    set_default: bool = False,
) -> None:
    """Register a new project.

    Args:
        project_name: The name of the project to register.
        set_project: Whether to set the project as active.
        display_name: The display name of the project.
        set_default: Whether to set the project as the default project.
    """
    check_zenml_pro_project_availability()
    client = Client()
    with console.status("Creating project...\n"):
        try:
            project = client.create_project(
                project_name,
                description="",
                display_name=display_name,
            )
            cli_utils.success("✔ Project created successfully.")
        except Exception as e:
            cli_utils.error(str(e))

    if set_project:
        client.set_active_project(project_name)
        cli_utils.success(
            f"✔ The active project has been set to {project_name}"
        )

    if set_default:
        client.update_user(
            name_id_or_prefix=client.active_user.id,
            updated_default_project_id=project.id,
        )
        cli_utils.success(
            f"✔ The default project has been set to {project.name}"
        )


@project.command("set")
@click.argument("project_name_or_id", type=str, required=True)
@click.option(
    "--default",
    "default",
    is_flag=True,
    help="Set this project as the default project.",
)
def set_project(project_name_or_id: str, default: bool = False) -> None:
    """Set the active project.

    Args:
        project_name_or_id: The name or ID of the project to set as active.
        default: Whether to set the project as the default project.
    """
    check_zenml_pro_project_availability()
    client = Client()
    with console.status("Setting project...\n"):
        try:
            project = client.set_active_project(project_name_or_id)
            cli_utils.success(
                f"✔ The active project has been set to {project_name_or_id}"
            )
        except Exception as e:
            cli_utils.error(str(e))

    if default:
        client.update_user(
            name_id_or_prefix=client.active_user.id,
            updated_default_project_id=project.id,
        )
        cli_utils.declare(
            f"The default project has been set to {project.name}"
        )


@project.command("describe")
@click.argument("project_name_or_id", type=str, required=False)
def describe_project(project_name_or_id: Optional[str] = None) -> None:
    """Get the project.

    Args:
        project_name_or_id: The name or ID of the project to set as active.
    """
    check_zenml_pro_project_availability()
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


@project.command("delete")
@click.argument("project_name_or_id", type=str, required=True)
def delete_project(project_name_or_id: str) -> None:
    """Delete a project.

    Args:
        project_name_or_id: The name or ID of the project to delete.
    """
    check_zenml_pro_project_availability()
    client = Client()
    with console.status("Deleting project...\n"):
        try:
            client.delete_project(project_name_or_id)
            cli_utils.declare(
                f"Project '{project_name_or_id}' deleted successfully."
            )
        except Exception as e:
            cli_utils.error(str(e))
