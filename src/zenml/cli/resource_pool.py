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
    get_default_output_format,
    list_options,
)
from zenml.client import Client
from zenml.console import console
from zenml.enums import CliCategories, StackComponentType
from zenml.models import Page, ResourcePoolFilter, ResourceRequestResponse


@cli.group(cls=TagGroup, tag=CliCategories.MANAGEMENT_TOOLS)
def resource_pool() -> None:
    """Commands for interacting with resource pools."""


def _parse_capacity(capacity: str) -> Dict[str, int]:
    """Parse a JSON/YAML capacity string into int values.

    Args:
        capacity: The capacity string to parse.

    Raises:
        ValueError: If the capacity string is invalid.

    Returns:
        A dictionary of resource types and their capacities.
    """
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
    "-c",
    type=str,
    required=True,
    help="Resource pool capacity in JSON or YAML. "
    'Example: \'{"gpu": 2, "cpu": 8}\'.',
)
@click.option(
    "--description",
    "-d",
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
    "-c",
    type=str,
    required=False,
    help=(
        "Updated capacity in JSON or YAML. Setting a value to 0 removes the "
        "resource from the pool. Example: '{\"gpu\": 0}'."
    ),
)
@click.option(
    "--description",
    "-d",
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


@resource_pool.command(
    "attach",
    help="Attach a component to a resource pool.",
)
@click.argument("resource_pool", type=str, required=True)
@click.argument("component", type=str, required=True)
@click.option(
    "--priority",
    "-p",
    type=int,
    required=True,
    help="Priority of this pool for the component. Higher means preferred.",
)
def attach_component_to_resource_pool(
    resource_pool: str,
    component: str,
    priority: int,
) -> None:
    """Attach a component to a resource pool.

    Args:
        resource_pool: Name, ID or prefix of the resource pool.
        component: Name, ID or prefix of the component.
        priority: Priority of the assignment.
    """
    with console.status("Attaching component to resource pool...\n"):
        try:
            pool = Client().get_resource_pool(
                name_id_or_prefix=resource_pool, hydrate=False
            )
            component_model = Client().get_stack_component(
                name_id_or_prefix=component,
                component_type=StackComponentType.ORCHESTRATOR,
                allow_name_prefix_match=False,
                hydrate=False,
            )
            Client().update_resource_pool(
                name_id_or_prefix=pool.id,
                attach_components={component_model.id: priority},
            )
        except Exception as err:
            cli_utils.exception(err)
        else:
            cli_utils.declare(
                f"Attached component `{component_model.name}` to resource pool "
                f"`{pool.name}` with priority {priority}."
            )


@resource_pool.command(
    "detach",
    help="Detach a component from a resource pool.",
)
@click.argument("resource_pool", type=str, required=True)
@click.argument("component", type=str, required=True)
def detach_component_from_resource_pool(
    resource_pool: str,
    component: str,
) -> None:
    """Detach a component from a resource pool.

    Args:
        resource_pool: Name, ID or prefix of the resource pool.
        component: Name, ID or prefix of the component.
    """
    with console.status("Detaching component from resource pool...\n"):
        try:
            pool = Client().get_resource_pool(
                name_id_or_prefix=resource_pool, hydrate=False
            )
            component_model = Client().get_stack_component(
                name_id_or_prefix=component,
                component_type=StackComponentType.ORCHESTRATOR,
                allow_name_prefix_match=False,
                hydrate=False,
            )
            Client().update_resource_pool(
                name_id_or_prefix=pool.id,
                detach_components=[component_model.id],
            )
        except Exception as err:
            cli_utils.exception(err)
        else:
            cli_utils.declare(
                f"Detached component `{component_model.name}` from resource "
                f"pool `{pool.name}`."
            )


@resource_pool.command(
    "requests",
    help="List queued and/or active resource requests for a resource pool.",
)
@click.argument("pool", type=str, required=True)
@click.option(
    "--view",
    type=click.Choice(["queued", "active", "all"]),
    default="all",
    show_default=True,
    help="Which requests to show for this pool.",
)
@click.option(
    "--columns",
    "-c",
    type=str,
    default="id,state,status,component,step_run,created",
    help="Comma-separated list of columns to display, or 'all' for all columns.",
)
@click.option(
    "--output",
    "-o",
    "output_format",
    type=click.Choice(["table", "json", "yaml", "tsv", "csv"]),
    default=get_default_output_format(),
    help="Output format for the list.",
)
def list_resource_pool_requests(
    pool: str,
    view: str,
    columns: str,
    output_format: OutputFormat,
) -> None:
    """List queued and/or active resource requests for a resource pool.

    Args:
        pool: Name, ID or prefix of the resource pool.
        view: Which requests to show ("queued", "active", or "all").
        columns: Output columns.
        output_format: Output format.
    """
    with console.status("Loading resource pool requests...\n"):
        pool_model = Client().get_resource_pool(
            name_id_or_prefix=pool, hydrate=True
        )

    if view == "queued":
        items = list(item.request for item in pool_model.queued_requests)
        state_by_id = {r.id: "queued" for r in items}
    elif view == "active":
        items = list(item.request for item in pool_model.active_requests)
        state_by_id = {r.id: "active" for r in items}
    else:
        active = list(item.request for item in pool_model.active_requests)
        queued = list(item.request for item in pool_model.queued_requests)
        items = [*active, *queued]
        state_by_id = {r.id: "active" for r in active}
        state_by_id.update({r.id: "queued" for r in queued})

    page: Page["ResourceRequestResponse"] = Page(
        index=1,
        max_size=max(1, len(items)),
        total_pages=1,
        total=len(items),
        items=items,
    )

    def _row_with_state(item: Any, _: OutputFormat) -> dict[str, Any]:
        return {"state": state_by_id.get(item.id, "unknown")}

    cli_utils.print_page(
        page=page,
        columns=columns,
        output_format=output_format,
        row_formatter=_row_with_state,
        empty_message=(
            f"No {view} resource requests found for resource pool "
            f"`{pool_model.name}`."
            if view != "all"
            else "No resource requests found for resource pool "
            f"`{pool_model.name}`."
        ),
    )
