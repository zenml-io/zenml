#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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

from typing import TYPE_CHECKING, List, Optional, cast

import click

from zenml.cli import utils as cli_utils
from zenml.cli.cli import cli
from zenml.core.repo import Repository

if TYPE_CHECKING:
    from zenml.metadata_stores import BaseMetadataStore


@cli.group("metadata-store")
def metadata_store() -> None:
    """Utilities for metadata store"""


@metadata_store.command("get")
def get_active_metadata_store() -> None:
    """Gets the metadata store of the active stack."""
    metadata_store_name = Repository().get_active_stack().metadata_store_name
    cli_utils.declare(f"Active metadata store: {metadata_store_name}")


@metadata_store.command(
    "register", context_settings=dict(ignore_unknown_options=True)
)
@click.argument("name", type=click.STRING, required=True)
@click.option(
    "--type",
    "-t",
    help="The type of the metadata store to register.",
    required=True,
    type=click.STRING,
)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
@cli_utils.activate_integrations
def register_metadata_store(name: str, type: str, args: List[str]) -> None:
    """Register a metadata store."""

    try:
        parsed_args = cli_utils.parse_unknown_options(args)
    except AssertionError as e:
        cli_utils.error(str(e))
        return

    repo: Repository = Repository()
    try:
        # TODO [ENG-187]: Remove when we rework the registry logic
        from zenml.core.component_factory import metadata_store_factory

        comp = metadata_store_factory.get_single_component(type)
    except AssertionError as e:
        cli_utils.error(str(e))
        return

    metadata_store = comp(repo_path=repo.path, **parsed_args)
    service = repo.get_service()
    service.register_metadata_store(
        name, cast("BaseMetadataStore", metadata_store)
    )
    cli_utils.declare(f"Metadata Store `{name}` successfully registered!")


@metadata_store.command("list")
def list_metadata_stores() -> None:
    """List all available metadata stores from service."""
    repo = Repository()
    service = repo.get_service()
    if len(service.metadata_stores) == 0:
        cli_utils.warning("No metadata stores registered!")
        return

    active_metadata_store = repo.get_active_stack().metadata_store_name

    cli_utils.title("Metadata Stores:")
    cli_utils.print_table(
        cli_utils.format_component_list(
            service.metadata_stores, active_metadata_store
        )
    )


@metadata_store.command(
    "describe",
    help="Show details about the current active metadata store.",
)
@click.argument(
    "metadata_store_name",
    type=click.STRING,
    required=False,
)
def describe_metadata_store(metadata_store_name: Optional[str]) -> None:
    """Show details about the current active metadata store."""
    repo = Repository()
    metadata_store_name = (
        metadata_store_name or repo.get_active_stack().metadata_store_name
    )

    metadata_stores = repo.get_service().metadata_stores
    if len(metadata_stores) == 0:
        cli_utils.warning("No metadata stores registered!")
        return

    try:
        metadata_store_details = metadata_stores[metadata_store_name]
    except KeyError:
        cli_utils.error(
            f"Metadata store `{metadata_store_name}` does not exist."
        )
        return
    cli_utils.title("Metadata Store:")
    if repo.get_active_stack().metadata_store_name == metadata_store_name:
        cli_utils.declare("**ACTIVE**\n")
    else:
        cli_utils.declare("")
    cli_utils.declare(f"NAME: {metadata_store_name}")
    cli_utils.print_component_properties(metadata_store_details.dict())


@metadata_store.command("delete")
@click.argument("metadata_store_name", type=str)
def delete_metadata_store(metadata_store_name: str) -> None:
    """Delete a metadata store."""
    service = Repository().get_service()
    service.delete_metadata_store(metadata_store_name)
    cli_utils.declare(f"Deleted metadata store: {metadata_store_name}")
