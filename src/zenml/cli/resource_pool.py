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
"""Resource pool CLI commands."""

from typing import Any, Dict, Optional

import click

from zenml.cli import utils as cli_utils
from zenml.cli.cli import TagGroup, cli
from zenml.cli.utils import (
    OutputFormat,
    convert_structured_str_to_dict,
    list_options,
)
from zenml.client import Client
from zenml.console import console
from zenml.enums import CliCategories
from zenml.models import ResourcePoolFilter


@cli.group(cls=TagGroup, tag=CliCategories.MANAGEMENT_TOOLS)
def resource_pool() -> None:
    """Commands for interacting with resource pools."""


def _parse_capacity(capacity: str) -> Dict[str, int]:
    """Parse a JSON/YAML capacity string into int values."""

    raw = convert_structured_str_to_dict(capacity)
    parsed: Dict[str, int] = {}
    for key, value in raw.items():
        try:
            parsed[key] = int(value)
        except (TypeError, ValueError) as e:
            raise ValueError(
                f"Invalid capacity value for key '{key}': {value!r}. "
                "Capacity values must be integers."
            ) from e
    return parsed


@resource_pool.command("create", help="Create a resource pool.")
@click.argument("name", type=str, required=True)
@click.option(
    "--capacity",
    type=str,
    required=True,
    help="Resource pool capacity in JSON or YAML. "
    'Example: \'{"gpu": 2, "cpu": 8}\'.',
)
@click.option(
    "--description",
    type=str,
    required=False,
    help="Optional description for the resource pool.",
)
def create_resource_pool(
    name: str, capacity: str, description: Optional[str] = None
) -> None:
    """Create a resource pool.

    Args:
        name: Name of the resource pool.
        capacity: Capacity in JSON or YAML.
        description: Optional description.
    """
    try:
        parsed_capacity = _parse_capacity(capacity)
    except ValueError as err:
        cli_utils.exception(err)
        return

    with console.status(f"Creating resource pool '{name}'...\n"):
        try:
            resource_pool_ = Client().create_resource_pool(
                name=name, capacity=parsed_capacity, description=description
            )
        except Exception as err:
            cli_utils.exception(err)
        else:
            cli_utils.declare(
                f"Successfully created resource pool `{resource_pool_.name}`."
            )


@resource_pool.command("update", help="Update a resource pool.")
@click.argument("name_id_or_prefix", type=str, required=True)
@click.option(
    "--capacity",
    type=str,
    required=False,
    help=(
        "Updated capacity in JSON or YAML. Setting a value to 0 removes the "
        "resource from the pool. Example: '{\"gpu\": 0}'."
    ),
)
@click.option(
    "--description",
    type=str,
    required=False,
    help="Updated description for the resource pool.",
)
def update_resource_pool(
    name_id_or_prefix: str,
    capacity: Optional[str] = None,
    description: Optional[str] = None,
) -> None:
    """Update a resource pool.

    Args:
        name_id_or_prefix: Name, ID or prefix of the resource pool.
        capacity: Updated capacity in JSON or YAML.
        description: Updated description.
    """
    if capacity is None and description is None:
        cli_utils.declare("No updates specified.")
        return

    parsed_capacity = None
    if capacity is not None:
        try:
            parsed_capacity = _parse_capacity(capacity)
        except ValueError as err:
            cli_utils.exception(err)
            return

    with console.status("Updating resource pool...\n"):
        try:
            resource_pool_ = Client().update_resource_pool(
                name_id_or_prefix=name_id_or_prefix,
                description=description,
                capacity=parsed_capacity,
            )
        except Exception as err:
            cli_utils.exception(err)
        else:
            cli_utils.declare(
                f"Successfully updated resource pool `{resource_pool_.name}`."
            )


@resource_pool.command("describe", help="Describe a resource pool.")
@click.argument("name_id_or_prefix", type=str, required=True)
def describe_resource_pool(name_id_or_prefix: str) -> None:
    """Describe a resource pool.

    Args:
        name_id_or_prefix: Name, ID or prefix of the resource pool.
    """
    try:
        resource_pool_ = Client().get_resource_pool(
            name_id_or_prefix=name_id_or_prefix, hydrate=True
        )
    except KeyError as err:
        cli_utils.exception(err)
    else:
        cli_utils.print_pydantic_model(
            title=f"Resource pool '{resource_pool_.name}'",
            model=resource_pool_,
        )


@resource_pool.command("list", help="List resource pools.")
@list_options(
    ResourcePoolFilter,
    default_columns=["id", "name", "capacity", "occupied_resources"],
)
def list_resource_pools(
    columns: str, output_format: OutputFormat, **kwargs: Any
) -> None:
    """List resource pools.

    Args:
        columns: Columns to display in output.
        output_format: Format for output (table/json/yaml/csv/tsv).
        **kwargs: Keyword arguments to filter resource pools by.
    """
    with console.status("Listing resource pools...\n"):
        pools = Client().list_resource_pools(**kwargs, hydrate=True)

    cli_utils.print_page(
        pools,
        columns,
        output_format,
        empty_message="No resource pools found for this filter.",
    )


@resource_pool.command("delete", help="Delete a resource pool.")
@click.argument("name_id_or_prefix", type=str, required=True)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Don't ask for confirmation.",
)
def delete_resource_pool(name_id_or_prefix: str, yes: bool = False) -> None:
    """Delete a resource pool.

    Args:
        name_id_or_prefix: Name, ID or prefix of the resource pool.
        yes: If set, don't ask for confirmation.
    """
    if not yes:
        confirmation = cli_utils.confirmation(
            "Are you sure you want to delete resource pool "
            f"`{name_id_or_prefix}`?"
        )
        if not confirmation:
            cli_utils.declare("Resource pool deletion canceled.")
            return

    with console.status("Deleting resource pool...\n"):
        try:
            Client().delete_resource_pool(name_id_or_prefix=name_id_or_prefix)
        except Exception as err:
            cli_utils.exception(err)
        else:
            cli_utils.declare(f"Deleted resource pool `{name_id_or_prefix}`.")
