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
    is_sorted_or_filtered,
    list_options,
    warn_unsupported_non_default_workspace,
)
from zenml.client import Client
from zenml.console import console
from zenml.enums import CliCategories
from zenml.models import WorkspaceFilter


@cli.group(cls=TagGroup, tag=CliCategories.MANAGEMENT_TOOLS)
def workspace() -> None:
    """Commands for workspace management."""


@workspace.command("list", hidden=True)
@list_options(WorkspaceFilter)
@click.pass_context
def list_workspaces(ctx: click.Context, **kwargs: Any) -> None:
    """List all workspaces.

    Args:
        ctx: The click context object
        **kwargs: Keyword arguments to filter the list of workspaces.
    """
    warn_unsupported_non_default_workspace()
    client = Client()
    with console.status("Listing workspaces...\n"):
        workspaces = client.list_workspaces(**kwargs)
        if workspaces:
            cli_utils.print_pydantic_models(
                workspaces,
                exclude_columns=["id", "created", "updated"],
                active_models=[Client().active_workspace],
                show_active=not is_sorted_or_filtered(ctx),
            )
        else:
            cli_utils.declare("No workspaces found for the given filter.")


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
