#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""CLI functionality to interact with hook invocations."""

from typing import Any
from uuid import UUID

import click

from zenml.cli import utils as cli_utils
from zenml.cli.cli import TagGroup, cli
from zenml.cli.utils import OutputFormat, list_options
from zenml.client import Client
from zenml.console import console
from zenml.enums import CliCategories
from zenml.models import HookInvocationFilter


@cli.group(cls=TagGroup, tag=CliCategories.MANAGEMENT_TOOLS)
def hook_invocation() -> None:
    """Commands for interacting with hook invocations."""


@hook_invocation.command("list", help="List hook invocations.")
@list_options(
    HookInvocationFilter,
    default_columns=[
        "id",
        "name",
        "hook_type",
        "status",
        "pipeline_run_id",
        "step_run_id",
        "start_time",
    ],
)
def list_hook_invocations(
    columns: str, output_format: OutputFormat, **kwargs: Any
) -> None:
    """List hook invocations.

    Args:
        columns: Columns to display in output.
        output_format: Format for output (table/json/yaml/csv/tsv).
        **kwargs: Keyword arguments to filter hook invocations.
    """
    with console.status("Listing hook invocations...\n"):
        hook_invocations = Client().list_hook_invocations(**kwargs)

    cli_utils.print_page(
        hook_invocations,
        columns,
        output_format,
        empty_message="No hook invocations found for the given filters.",
    )


@hook_invocation.command("describe", help="Describe a hook invocation.")
@click.argument("hook_invocation_id", type=str, required=True)
def describe_hook_invocation(hook_invocation_id: str) -> None:
    """Describe a hook invocation.

    Args:
        hook_invocation_id: ID of the hook invocation.
    """
    try:
        hook_invocation = Client().get_hook_invocation(
            hook_invocation_id=UUID(hook_invocation_id)
        )
    except KeyError as err:
        cli_utils.exception(err)
    else:
        cli_utils.print_pydantic_model(
            title=f"Hook invocation '{hook_invocation.id}'",
            model=hook_invocation,
        )


@hook_invocation.command("delete", help="Delete a hook invocation.")
@click.argument("hook_invocation_id", type=str, required=True)
def delete_hook_invocation(hook_invocation_id: str) -> None:
    """Delete a hook invocation.

    Args:
        hook_invocation_id: ID of the hook invocation.
    """
    try:
        Client().delete_hook_invocation(
            hook_invocation_id=UUID(hook_invocation_id)
        )
    except KeyError as err:
        cli_utils.exception(err)
    else:
        cli_utils.declare(f"Deleted hook invocation '{hook_invocation_id}'.")
