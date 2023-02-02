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
"""Functionality to administer workspaces of the ZenML CLI and server."""

from typing import Any, Optional

import click

from zenml.cli import utils as cli_utils
from zenml.cli.cli import TagGroup, cli
from zenml.cli.utils import (
    list_options,
    warn_unsupported_non_default_workspace,
)
from zenml.client import Client
from zenml.console import console
from zenml.enums import CliCategories
from zenml.exceptions import EntityExistsError, IllegalOperationError
from zenml.models import WorkspaceFilterModel


@cli.group(cls=TagGroup, tag=CliCategories.MANAGEMENT_TOOLS)
def workspace() -> None:
    """Commands for workspace management."""


@workspace.command("list", hidden=True)
@list_options(WorkspaceFilterModel)
def list_workspaces(**kwargs: Any) -> None:
    """List all workspaces.

    Args:
        **kwargs: Keyword arguments to filter the list of workspaces.
    """
    warn_unsupported_non_default_workspace()
    cli_utils.print_active_config()
    client = Client()
    with console.status("Listing workspaces...\n"):

        workspaces = client.list_workspaces(**kwargs)
        if workspaces:
            active_workspace = Client().active_workspace
            active_workspace_id = (
                active_workspace.id if active_workspace else None
            )
            cli_utils.print_pydantic_models(
                workspaces,
                exclude_columns=["id", "created", "updated"],
                is_active=(lambda p: p.id == active_workspace_id),
            )
        else:
            cli_utils.declare("No workspaces found for the given filter.")


@workspace.command("create", help="Create a new workspace.", hidden=True)
@click.argument("workspace_name", type=str, required=True)
@click.option("--description", "-d", type=str, required=False, default="")
def create_workspace(workspace_name: str, description: str) -> None:
    """Create a new workspace.

    Args:
        workspace_name: The name of the workspace.
        description: A description of the workspace.
    """
    warn_unsupported_non_default_workspace()
    cli_utils.print_active_config()
    try:
        Client().create_workspace(name=workspace_name, description=description)
    except EntityExistsError as err:
        cli_utils.error(str(err))
    cli_utils.declare(f"Created workspace '{workspace_name}'.")


@workspace.command("update", help="Update an existing workspace.", hidden=True)
@click.argument("workspace_name", type=str, required=True)
@click.option(
    "--name",
    "-n",
    "new_name",
    type=str,
    required=False,
    help="New workspace name.",
)
@click.option(
    "--description",
    "-d",
    "new_description",
    type=str,
    required=False,
    help="New workspace description.",
)
def update_workspace(
    workspace_name: str,
    new_name: Optional[str] = None,
    new_description: Optional[str] = None,
) -> None:
    """Update an existing workspace.

    Args:
        workspace_name: The name of the workspace.
        new_name: The new name of the workspace.
        new_description: The new description of the workspace.
    """
    warn_unsupported_non_default_workspace()
    cli_utils.print_active_config()
    try:
        Client().update_workspace(
            name_id_or_prefix=workspace_name,
            new_name=new_name,
            new_description=new_description,
        )
    except (EntityExistsError, KeyError, IllegalOperationError) as err:
        cli_utils.error(str(err))
    cli_utils.declare(f"Updated workspace '{workspace_name}'.")


@workspace.command("describe", hidden=True)
@click.argument("workspace_name_or_id", type=str, required=False)
def describe_workspace(workspace_name_or_id: Optional[str] = None) -> None:
    """Get the workspace.

    Args:
        workspace_name_or_id: The name or ID of the workspace to set as active.
    """
    warn_unsupported_non_default_workspace()
    client = Client()
    if not workspace_name_or_id:
        active_workspace = client.active_workspace
        cli_utils.print_pydantic_models(
            [active_workspace], exclude_columns=["created", "updated"]
        )
    else:
        try:
            workspace_ = client.get_workspace(workspace_name_or_id)
        except KeyError as err:
            cli_utils.error(str(err))
        else:
            cli_utils.print_pydantic_models(
                [workspace_], exclude_columns=["created", "updated"]
            )


@workspace.command("set", help="Set the active workspace.", hidden=True)
@click.argument("workspace_name_or_id", type=str, required=True)
def set_workspace(workspace_name_or_id: str) -> None:
    """Set the active workspace.

    Args:
        workspace_name_or_id: The name or ID of the workspace to set as active.
    """
    warn_unsupported_non_default_workspace()
    cli_utils.print_active_config()
    try:
        Client().set_active_workspace(
            workspace_name_or_id=workspace_name_or_id
        )
    except KeyError as err:
        cli_utils.error(str(err))
    cli_utils.declare(f"Set active workspace '{workspace_name_or_id}'.")


@workspace.command("delete", help="Delete a workspace.", hidden=True)
@click.argument("workspace_name_or_id", type=str, required=True)
def delete_workspace(workspace_name_or_id: str) -> None:
    """Delete a workspace.

    Args:
        workspace_name_or_id: Name or ID of workspace to delete.
    """
    warn_unsupported_non_default_workspace()
    cli_utils.print_active_config()
    confirmation = cli_utils.confirmation(
        f"Are you sure you want to delete workspace `{workspace_name_or_id}`? "
        "This will permanently delete all associated stacks, stack components, "
        "pipelines, runs, artifacts and metadata."
    )
    if not confirmation:
        cli_utils.declare("Project deletion canceled.")
        return
    try:
        Client().delete_workspace(workspace_name_or_id)
    except (KeyError, IllegalOperationError) as err:
        cli_utils.error(str(err))
    cli_utils.declare(f"Deleted workspace '{workspace_name_or_id}'.")


@cli.group(cls=TagGroup, tag=CliCategories.MANAGEMENT_TOOLS)
def project() -> None:
    """Deprecated commands for project management."""
    cli_utils.warning(
        "DEPRECATION WARNING: `project` has been renamed to"
        "`workspace`. Please switch to using "
        "`zenml workspace ...`."
    )


project.add_command(list_workspaces)
project.add_command(describe_workspace)
project.add_command(create_workspace)
project.add_command(update_workspace)
project.add_command(set_workspace)
project.add_command(delete_workspace)
