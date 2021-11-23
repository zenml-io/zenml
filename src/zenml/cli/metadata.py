#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.

from typing import List

import click

from zenml.cli import utils as cli_utils
from zenml.cli.cli import cli
from zenml.core.repo import Repository


@cli.group()
def metadata() -> None:
    """Utilities for metadata store"""


@metadata.command("get")
def get_active_metadata_store() -> None:
    """Gets the metadata store of the active stack."""
    metadata_store_name = Repository().get_active_stack().metadata_store_name
    cli_utils.declare(f"Active metadata store: {metadata_store_name}")


@metadata.command(
    "register", context_settings=dict(ignore_unknown_options=True)
)
@click.argument("metadata_store_name", type=str)
@click.argument("metadata_store_type", type=str)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
@cli_utils.activate_integrations
def register_metadata_store(
    metadata_store_name: str, metadata_store_type: str, args: List[str]
) -> None:
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

        comp = metadata_store_factory.get_single_component(metadata_store_type)
    except AssertionError as e:
        cli_utils.error(str(e))
        return

    metadata_store = comp(**parsed_args)
    service = repo.get_service()
    service.register_metadata_store(metadata_store_name, metadata_store)
    cli_utils.declare(
        f"Metadata Store `{metadata_store_name}` successfully registered!"
    )


@metadata.command("list")
def list_metadata_stores() -> None:
    """List all available metadata stores from service."""
    service = Repository().get_service()
    cli_utils.title("Metadata Stores:")
    cli_utils.echo_component_list(service.metadata_stores)


@metadata.command("delete")
@click.argument("metadata_store_name", type=str)
def delete_metadata_store(metadata_store_name: str) -> None:
    """Delete a metadata store."""
    service = Repository().get_service()
    service.delete_metadata_store(metadata_store_name)
    cli_utils.declare(f"Deleted metadata store: {metadata_store_name}")
