#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""CLI functionality to interact with authorized devices."""

from typing import Any

import click

from zenml.cli import utils as cli_utils
from zenml.cli.cli import TagGroup, cli
from zenml.cli.utils import list_options
from zenml.client import Client
from zenml.console import console
from zenml.enums import CliCategories
from zenml.logger import get_logger
from zenml.models import OAuthDeviceFilter

logger = get_logger(__name__)


@cli.group(cls=TagGroup, tag=CliCategories.MANAGEMENT_TOOLS)
def authorized_device() -> None:
    """Interact with authorized devices."""


@authorized_device.command("describe")
@click.argument("id_or_prefix", type=str, required=True)
def describe_authorized_device(id_or_prefix: str) -> None:
    """Fetch an authorized device.

    Args:
        id_or_prefix: The ID of the authorized device to fetch.
    """
    try:
        device = Client().get_authorized_device(
            id_or_prefix=id_or_prefix,
        )
    except KeyError as e:
        cli_utils.error(str(e))

    cli_utils.print_pydantic_model(
        title=f"Authorized device `{device.id}`",
        model=device,
        exclude_columns={"user"},
    )


@authorized_device.command(
    "list", help="List all authorized devices for the current user."
)
@list_options(OAuthDeviceFilter)
def list_authorized_devices(**kwargs: Any) -> None:
    """List all authorized devices.

    Args:
        **kwargs: Keyword arguments to filter authorized devices.
    """
    with console.status("Listing authorized devices...\n"):
        devices = Client().list_authorized_devices(**kwargs)

        if not devices.items:
            cli_utils.declare("No authorized devices found for this filter.")
            return

        cli_utils.print_pydantic_models(
            devices,
            columns=["id", "status", "ip_address", "hostname", "os"],
        )


@authorized_device.command("lock")
@click.argument("id", type=str, required=True)
def lock_authorized_device(id: str) -> None:
    """Lock an authorized device.

    Args:
        id: The ID of the authorized device to lock.
    """
    try:
        Client().update_authorized_device(
            id_or_prefix=id,
            locked=True,
        )
    except KeyError as e:
        cli_utils.error(str(e))
    else:
        cli_utils.declare(f"Locked authorized device `{id}`.")


@authorized_device.command("unlock")
@click.argument("id", type=str, required=True)
def unlock_authorized_device(id: str) -> None:
    """Unlock an authorized device.

    Args:
        id: The ID of the authorized device to unlock.
    """
    try:
        Client().update_authorized_device(
            id_or_prefix=id,
            locked=False,
        )
    except KeyError as e:
        cli_utils.error(str(e))
    else:
        cli_utils.declare(f"Locked authorized device `{id}`.")


@authorized_device.command("delete")
@click.argument("id", type=str, required=True)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Don't ask for confirmation.",
)
def delete_authorized_device(id: str, yes: bool = False) -> None:
    """Delete an authorized device.

    Args:
        id: The ID of the authorized device to delete.
        yes: If set, don't ask for confirmation.
    """
    if not yes:
        confirmation = cli_utils.confirmation(
            f"Are you sure you want to delete authorized device `{id}`?"
        )
        if not confirmation:
            cli_utils.declare("Authorized device deletion canceled.")
            return

    try:
        Client().delete_authorized_device(id_or_prefix=id)
    except KeyError as e:
        cli_utils.error(str(e))
    else:
        cli_utils.declare(f"Deleted authorized device `{id}`.")
