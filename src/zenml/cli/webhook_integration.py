# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""CLI commands for webhook integrations."""

from typing import Any

import click

from zenml.cli import utils as cli_utils
from zenml.cli.cli import TagGroup, cli
from zenml.cli.utils import OutputFormat, list_options
from zenml.client import Client
from zenml.console import console
from zenml.enums import CliCategories, WebhookType
from zenml.models import WebhookIntegrationFilter


@cli.group(
    "webhook-integration", cls=TagGroup, tag=CliCategories.MANAGEMENT_TOOLS
)
def webhook_integration() -> None:
    """Manage external webhook intake endpoints."""


@webhook_integration.command("create")
@click.argument("name", type=str)
@click.option(
    "--type",
    "webhook_type",
    type=click.Choice([value.value for value in WebhookType]),
    required=True,
)
@click.option("--secret", type=str, default=None)
@click.option("--inactive", is_flag=True, default=False)
def create_webhook_integration(
    name: str,
    webhook_type: str,
    secret: str | None,
    inactive: bool,
) -> None:
    """Create a webhook integration.

    Args:
        name: The integration name.
        webhook_type: The webhook provider type.
        secret: An optional user-supplied signing secret.
        inactive: Whether to create the integration inactive.
    """
    result = Client().create_webhook_integration(
        name=name,
        webhook_type=WebhookType(webhook_type),
        active=not inactive,
        secret=secret,
    )
    cli_utils.print_pydantic_model(
        title=f"Webhook integration '{name}'",
        model=result.integration,
    )
    if result.secret is not None:
        cli_utils.declare(
            f"Signing secret: {result.secret.get_secret_value()}"
        )


@webhook_integration.command("describe")
@click.argument("name_or_id", type=str)
def describe_webhook_integration(name_or_id: str) -> None:
    """Describe a webhook integration.

    Args:
        name_or_id: The integration name or ID.
    """
    integration = Client().get_webhook_integration(name_or_id)
    cli_utils.print_pydantic_model(
        title=f"Webhook integration '{integration.name}'",
        model=integration,
    )
    cli_utils.declare(f"Endpoint path: {integration.endpoint_path}")


@webhook_integration.command("list")
@list_options(
    WebhookIntegrationFilter,
    default_columns=["id", "name", "webhook_type", "active", "project"],
)
def list_webhook_integrations(
    columns: str, output_format: OutputFormat, **kwargs: Any
) -> None:
    """List webhook integrations.

    Args:
        columns: The columns to display.
        output_format: The output format.
        **kwargs: The webhook integration filters.
    """
    with console.status("Listing webhook integrations...\n"):
        integrations = Client().list_webhook_integrations(**kwargs)
    cli_utils.print_page(
        integrations,
        columns,
        output_format,
        empty_message="No webhook integrations found for this filter.",
    )


@webhook_integration.command("update")
@click.argument("name_or_id", type=str)
@click.option("--name", "new_name", type=str, default=None)
@click.option(
    "--active/--inactive", "active", default=None, help="Set active state."
)
def update_webhook_integration(
    name_or_id: str, new_name: str | None, active: bool | None
) -> None:
    """Update a webhook integration.

    Args:
        name_or_id: The integration name or ID.
        new_name: The new integration name.
        active: The new active state.
    """
    integration = Client().update_webhook_integration(
        name_id_or_prefix=name_or_id, name=new_name, active=active
    )
    cli_utils.print_pydantic_model(
        title=f"Webhook integration '{integration.name}'",
        model=integration,
    )


@webhook_integration.command("rotate-secret")
@click.argument("name_or_id", type=str)
@click.option("--secret", type=str, default=None)
def rotate_webhook_integration_secret(
    name_or_id: str, secret: str | None
) -> None:
    """Rotate a webhook integration signing secret.

    Args:
        name_or_id: The integration name or ID.
        secret: An optional user-supplied replacement secret.
    """
    result = Client().rotate_webhook_integration_secret(
        name_id_or_prefix=name_or_id, secret=secret
    )
    cli_utils.declare(f"Signing secret: {result.secret.get_secret_value()}")


@webhook_integration.command("delete")
@click.argument("name_or_id", type=str)
@click.option("--yes", "confirmed", is_flag=True)
def delete_webhook_integration(name_or_id: str, confirmed: bool) -> None:
    """Delete a webhook integration.

    Args:
        name_or_id: The integration name or ID.
        confirmed: Whether to skip the confirmation prompt.
    """
    if not confirmed and not cli_utils.confirmation(
        f"Delete webhook integration `{name_or_id}`?"
    ):
        return
    Client().delete_webhook_integration(name_or_id)
    cli_utils.declare(f"Deleted webhook integration `{name_or_id}`.")
