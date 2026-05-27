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
from zenml.models import (
    Page,
    ResourcePolicyGrant,
    ResourcePolicyResponse,
    ResourcePoolCapacityClass,
    ResourcePoolFilter,
    ResourcePoolReclaimable,
    ResourceRequestResponse,
)


@cli.group(cls=TagGroup, tag=CliCategories.MANAGEMENT_TOOLS)
def resource_pool() -> None:
    """Commands for interacting with resource pools."""


def _parse_resources(resources: str) -> Dict[str, int]:
    """Parse a JSON/YAML resources string into int values.

    Args:
        resources: The resources string to parse.

    Raises:
        ValueError: If the resources string is invalid.

    Returns:
        A dictionary of resource types and their values.
    """
    raw = convert_structured_str_to_dict(resources)
    parsed: Dict[str, int] = {}
    for key, value in raw.items():
        try:
            parsed[key] = int(value)
        except (TypeError, ValueError) as e:
            raise ValueError(
                f"Invalid resource value for key '{key}': {value!r}. "
                "Resource values must be integers."
            ) from e
    return parsed


def _resource_dict_to_capacity(
    resources: Dict[str, int],
) -> list[ResourcePoolCapacityClass]:
    """Convert CLI resource shorthand into capacity class entries.

    Args:
        resources: Mapping of resource descriptor names to declared capacity
            quantities.

    Returns:
        Capacity class entries using the compatibility ``default`` class.
    """
    return [
        ResourcePoolCapacityClass(
            resource=resource,
            class_name="default",
            quantity=quantity,
            rank=0,
            reclaimable=ResourcePoolReclaimable.NEVER,
        )
        for resource, quantity in resources.items()
    ]


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
        parsed_capacity = _parse_resources(capacity)
    except ValueError as err:
        cli_utils.exception(err)

    with console.status(f"Creating resource pool '{name}'...\n"):
        try:
            resource_pool_ = Client().create_resource_pool(
                name=name,
                capacity=_resource_dict_to_capacity(parsed_capacity),
                description=description,
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
            parsed_capacity = _parse_resources(capacity)
        except ValueError as err:
            cli_utils.exception(err)
            return

    with console.status("Updating resource pool...\n"):
        try:
            resource_pool_ = Client().update_resource_pool(
                name_id_or_prefix=name_id_or_prefix,
                description=description,
                capacity=_resource_dict_to_capacity(parsed_capacity)
                if parsed_capacity is not None
                else None,
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
    "attach-policy",
    help="Attach a policy to a resource pool.",
)
@click.argument("resource_pool", type=str, required=True)
@click.argument("component", type=str, required=True)
@click.option(
    "--component-type",
    "-t",
    type=click.Choice(
        [
            StackComponentType.ORCHESTRATOR.value,
            StackComponentType.STEP_OPERATOR.value,
        ]
    ),
    default=StackComponentType.ORCHESTRATOR.value,
    help="Type of the component to attach the policy to.",
)
@click.option(
    "--priority",
    "-p",
    type=int,
    required=True,
    help="Priority of this pool for the component. Higher means preferred.",
)
@click.option(
    "--reserved",
    "-r",
    type=str,
    required=True,
    help="Resources that are reserved for the component.",
)
@click.option(
    "--limit",
    "-l",
    type=str,
    required=True,
    help="Maximum resources that the component can use.",
)
def attach_policy_to_resource_pool(
    resource_pool: str,
    component: str,
    component_type: StackComponentType,
    priority: int,
    reserved: str,
    limit: Optional[str] = None,
) -> None:
    """Attach a policy to a resource pool.

    Args:
        resource_pool: Name, ID or prefix of the resource pool.
        component: Name, ID or prefix of the component.
        component_type: Type of the component to attach the policy to.
        priority: Priority of the assignment.
        reserved: Resources that are reserved for the component.
        limit: Maximum resources that the component can use.
    """
    try:
        parsed_reserved = _parse_resources(reserved)
    except ValueError as err:
        cli_utils.exception(err)

    parsed_limit = None
    if limit is not None:
        try:
            parsed_limit = _parse_resources(limit)
        except ValueError as err:
            cli_utils.exception(err)

    with console.status("Attaching pool policy to resource pool...\n"):
        try:
            pool = Client().get_resource_pool(
                name_id_or_prefix=resource_pool, hydrate=False
            )
            component_model = Client().get_stack_component(
                name_id_or_prefix=component,
                component_type=component_type,
                allow_name_prefix_match=False,
                hydrate=False,
            )
            grants = [
                ResourcePolicyGrant(
                    resource=resource,
                    classes=["default"],
                    reserved=reserved_quantity,
                    limit=(parsed_limit or parsed_reserved).get(
                        resource, reserved_quantity
                    ),
                )
                for resource, reserved_quantity in parsed_reserved.items()
            ]
            Client().create_resource_policy(
                component_id=component_model.id,
                pool_id=pool.id,
                priority=priority,
                grants=grants,
            )
        except Exception as err:
            cli_utils.exception(err)
        else:
            cli_utils.declare(
                f"Attached pool policy for component `{component_model.name}` "
                f"to resource pool `{pool.name}` with priority {priority}."
            )


@resource_pool.command(
    "detach-policy",
    help="Detach a policy from a resource pool.",
)
@click.argument("resource_pool", type=str, required=True)
@click.argument("component", type=str, required=True)
@click.option(
    "--component-type",
    "-t",
    type=click.Choice(
        [
            StackComponentType.ORCHESTRATOR.value,
            StackComponentType.STEP_OPERATOR.value,
        ]
    ),
    default=StackComponentType.ORCHESTRATOR.value,
    help="Type of the component to detach the policy from.",
)
def detach_policy_from_resource_pool(
    resource_pool: str,
    component: str,
    component_type: StackComponentType,
) -> None:
    """Detach a policy from a resource pool.

    Args:
        resource_pool: Name, ID or prefix of the resource pool.
        component: Name, ID or prefix of the component.
        component_type: Type of the component to detach the policy from.

    Raises:
        KeyError: If no policy is found for the component in the resource pool.
    """
    with console.status("Detaching pool policy from resource pool...\n"):
        try:
            pool = Client().get_resource_pool(
                name_id_or_prefix=resource_pool, hydrate=False
            )
            component_model = Client().get_stack_component(
                name_id_or_prefix=component,
                component_type=component_type,
                allow_name_prefix_match=False,
                hydrate=False,
            )
            policies = Client().list_resource_policies(
                pool_id=pool.id,
                component_id=component_model.id,
                hydrate=False,
            )
            if not policies.items:
                raise KeyError(
                    f"No policy found for component `{component_model.name}` "
                    f"in resource pool `{pool.name}`."
                )
            Client().delete_resource_policy(policy_id=policies.items[0].id)
        except Exception as err:
            cli_utils.exception(err)
        else:
            cli_utils.declare(
                f"Detached pool policy for component `{component_model.name}` "
                f"from resource pool `{pool.name}`."
            )


@resource_pool.command(
    "list-policies",
    help=(
        "List subject policies (orchestrator components attached to pools with "
        "priority, reserved resources, and limits). Provide a pool and/or a "
        "component; at least one is required."
    ),
)
@click.argument("pool", type=str, required=False, default=None)
@click.option(
    "--component",
    "-c",
    type=str,
    required=False,
    help=(
        "Orchestrator component name or ID. If the pool is omitted, lists all "
        "policies for this component across pools. If the pool is set, only "
        "that component's policy for that pool is listed."
    ),
)
@click.option(
    "--component-type",
    "-t",
    type=click.Choice(
        [
            StackComponentType.ORCHESTRATOR.value,
            StackComponentType.STEP_OPERATOR.value,
        ]
    ),
    default=None,
    help="Type of the component to list the policies for.",
)
@click.option(
    "--columns",
    type=str,
    default="id,component_id,pool_id,priority,grants,created",
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
def list_resource_pool_policies(
    pool: Optional[str],
    component: Optional[str],
    component_type: Optional[StackComponentType],
    columns: str,
    output_format: OutputFormat,
) -> None:
    """List policies attached to resource pool subject(s).

    Provide a pool (positional or ``--pool``), a ``--component``, or both.
    Omitting the pool lists every policy for that orchestrator component.

    Args:
        pool: Optional positional pool name, ID, or prefix.
        component: Optional orchestrator component name or ID.
        component_type: Type of the component to list the policies for.
        columns: Columns to print.
        output_format: Output format for the table or structured data.
    """
    pool_id = None
    pool_label = pool
    with console.status("Loading resource pool policies...\n"):
        try:
            if pool is not None:
                pool_model = Client().get_resource_pool(
                    name_id_or_prefix=pool, hydrate=False
                )
                pool_id = pool_model.id
                pool_label = pool_model.name
            component_id = None
            if component is not None:
                component_model = Client().get_stack_component(
                    name_id_or_prefix=component,
                    component_type=component_type
                    or StackComponentType.ORCHESTRATOR,
                    allow_name_prefix_match=False,
                    hydrate=False,
                )
                component_id = component_model.id
            policies_page = Client().list_resource_policies(
                pool_id=pool_id,
                component_id=component_id,
                hydrate=True,
            )
        except Exception as err:
            cli_utils.exception(err)

    page: Page[ResourcePolicyResponse] = policies_page
    if pool is not None and component is not None:
        empty = (
            f"No policies found for resource pool `{pool_label}` and "
            f"component `{component}`."
        )
    elif pool is not None:
        empty = f"No policies found for resource pool `{pool_label}`."
    else:
        empty = f"No policies found for orchestrator component `{component}`."

    cli_utils.print_page(
        page=page,
        columns=columns,
        output_format=output_format,
        empty_message=empty,
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
        client = Client()
        pool_model = client.get_resource_pool(
            name_id_or_prefix=pool, hydrate=True
        )
        queued = client.list_resource_pool_queue(pool_model.id).items
        active = client.list_resource_pool_allocations(pool_model.id).items

    if view == "queued":
        items = [
            client.get_resource_request(item.request_id) for item in queued
        ]
        state_by_id = {r.id: "queued" for r in items}
    elif view == "active":
        items = [
            client.get_resource_request(item.request_id) for item in active
        ]
        state_by_id = {r.id: "active" for r in items}
    else:
        active_requests = [
            client.get_resource_request(item.request_id) for item in active
        ]
        queued_requests = [
            client.get_resource_request(item.request_id) for item in queued
        ]
        items = [*active_requests, *queued_requests]
        state_by_id = {r.id: "active" for r in active_requests}
        state_by_id.update({r.id: "queued" for r in queued_requests})

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
