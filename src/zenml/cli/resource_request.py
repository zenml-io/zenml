"""Resource request CLI commands."""

from typing import Any
from uuid import UUID

import click

from zenml.cli import utils as cli_utils
from zenml.cli.cli import TagGroup, cli
from zenml.cli.utils import OutputFormat, list_options
from zenml.client import Client
from zenml.console import console
from zenml.enums import CliCategories
from zenml.models import ResourceRequestFilter


@cli.group(cls=TagGroup, tag=CliCategories.MANAGEMENT_TOOLS)
def resource_request() -> None:
    """Commands for interacting with resource requests."""


@resource_request.command("describe", help="Describe a resource request.")
@click.argument("resource_request_id", type=str, required=True)
def describe_resource_request(resource_request_id: str) -> None:
    """Describe a resource request.

    Args:
        resource_request_id: ID of the resource request.
    """
    try:
        resource_request = Client().zen_store.get_resource_request(
            UUID(resource_request_id)
        )
    except KeyError as err:
        cli_utils.exception(err)
    else:
        cli_utils.print_pydantic_model(
            title=f"Resource request '{resource_request.id}'",
            model=resource_request,
        )


@resource_request.command("list", help="List resource requests.")
@list_options(
    ResourceRequestFilter,
    default_columns=["id", "status", "component", "step_run", "created"],
)
def list_resource_requests(
    columns: str, output_format: OutputFormat, **kwargs: Any
) -> None:
    """List resource requests.

    Args:
        columns: Columns to display in output.
        output_format: Format for output (table/json/yaml/csv/tsv).
        **kwargs: Keyword arguments used to build the filter model.
    """
    filter_model = ResourceRequestFilter(**kwargs)
    with console.status("Listing resource requests...\n"):
        page = Client().zen_store.list_resource_requests(
            filter_model=filter_model, hydrate=False
        )

    cli_utils.print_page(
        page,
        columns,
        output_format,
        empty_message="No resource requests found for this filter.",
    )


@resource_request.command("delete", help="Delete a resource request.")
@click.argument("resource_request_id", type=str, required=True)
def delete_resource_request(resource_request_id: str) -> None:
    """Delete a resource request.

    Args:
        resource_request_id: ID of the resource request.
    """
    Client().zen_store.delete_resource_request(UUID(resource_request_id))
